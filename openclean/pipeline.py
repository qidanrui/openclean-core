# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Data pipeline for processing datasets as streams of rows."""

from __future__ import annotations
from collections import Counter
from typing import Callable, Dict, List, Optional, Tuple, Type, Union

import pandas as pd

from openclean.data.stream.base import DatasetStream
from openclean.data.stream.csv import CSVFile
from openclean.data.stream.df import DataFrameStream
from openclean.data.types import Columns, Scalar, Schema
from openclean.function.eval.base import EvalFunction
from openclean.operator.stream.collector import Distinct, DataFrame, RowCount, Write
from openclean.operator.stream.consumer import StreamConsumer
from openclean.operator.stream.processor import StreamProcessor
from openclean.operator.transform.filter import Filter
from openclean.operator.transform.limit import Limit
from openclean.operator.transform.insert import InsCol
from openclean.operator.transform.rename import Rename
from openclean.operator.transform.select import Select
from openclean.operator.transform.update import Update
from openclean.profiling.dataset import ColumnProfiler, ProfileOperator
from openclean.profiling.datatype.convert import DatatypeConverter
from openclean.profiling.datatype.operator import Typecast


class DataPipeline(object):
    """The data pipeline allows to iterate over the rows that are the result of
    streaming an input data set through a pipeline of stream operators.

    The class implements the context manager interface.
    """
    def __init__(
        self, reader: DatasetStream,
        columns: Optional[Schema] = None,
        pipeline: Optional[StreamProcessor] = None
    ):
        """Initialize the data stream reader, schema information for the
        streamed rows, and the optional pipeline operators.

        Parameters
        ----------
        reader: openclean.data.stream.base.DatasetReader
            Reader for the data stream.
        pipeline: list of openclean.data.stream.processor.StreamProcessor,
                default=None
            List of operators in the pipeline fpr this stream processor.

        """
        self.reader = reader
        self.pipeline = pipeline if pipeline is not None else list()

    def __enter__(self):
        """Enter method for the context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the associated file handle when the context manager exits."""
        return False

    def append(
        self, op: StreamProcessor, columns: Optional[Schema] = None
    ) -> DataPipeline:
        """Return a modified stream processer with the given operator appended
        to the stream pipeline.

        Parameters
        ----------
        op: openclean.operator.stream.processor.StreamProcessor
            Stream operator that is appended to the pipeline of the returned
            stream processor.
        columns: list of string, default=None
            Optional (modified) list of column names for the schema of the data
            stream rows.

        Returns
        -------
        openclean.pipeline.DataPipeline
        """
        return DataPipeline(reader=self.reader, pipeline=self.pipeline + [op])

    def count(self) -> int:
        """Count the number of rows in a data stream.

        Returns
        -------
        int
        """
        return self.stream(RowCount())

    def delete(self, predicate: EvalFunction) -> DataPipeline:
        """Remove rows from the data stream that satisfy a given condition.

        Parameters
        ----------
        predicate: opencelan.function.eval.base.EvalFunction
            Evaluation function used to delete rows.

        Returns
        -------
        openclean.pipeline.DataPipeline
        """
        # Create a new stream processor with a negated filter operator appended
        # to the pipeline to remove rows from the stream.
        return self.append(Filter(predicate=predicate, negated=True))

    def distinct(
        self, columns: Optional[Columns] = None, names: Optional[Schema] = None
    ) -> Counter:
        """Get counts for all distinct values over all columns in the
        associated data stream. Allows the user to specify te list of columns
        for which they want to count values.

        Parameters
        ----------
        columns: int, str, or list of int or string, default=None
            References to the column(s) for which unique values are counted.
        names: int, str, or list of int or string, default=None
            Optional renaming for selected columns.

        Returns
        -------
        collections.Counter
        """
        op = Distinct()
        # If optional list of columns is given append a select operation first
        # to filter on those columns before running the data stream.
        if columns is not None:
            return self.select(columns=columns, names=names).stream(op)
        return self.stream(op)

    def filter(
        self, predicate: EvalFunction, limit: Optional[int] = None
    ) -> DataPipeline:
        """Filter rows in the data stream that satisfy a given condition.
        Allows to limit the number of rows in the returned data stream.

        Parameters
        ----------
        predicate: opencelan.function.eval.base.EvalFunction
            Evaluation function used to filter rows.
        limit: int, default=None
            Limit the number of rows in the filtered data stream.

        Returns
        -------
        openclean.pipeline.DataPipeline
        """
        # Create a new stream processor with a filter operator appended to the
        # pipeline.
        op = Filter(predicate=predicate)
        ds = self.append(op)
        # Append a limit operator to the returned dataset if a limit is given.
        return ds if limit is None else ds.limit(count=limit)

    def head(self, count: Optional[int] = 10) -> pd.DataFrame:
        """Return the first n rows in the data stream as a pandas data frame.
        This is a short-cut for using a pipeline of .limit() and .to_df().

        Parameters
        ----------
        count: int, default=10
            Defines the maximum number of rows in the returned data frame.

        Returns
        -------
        pd.DataFrame
        """
        return self.limit(count=count).to_df()

    def iterrows(self):
        """Simulate the iterrows() function of a pandas DataFrame as it is used
        in openclean. Returns an iterator that yields pairs of row identifier
        and value list for each row in the streamed data frame.
        """
        if self.pipeline:
            consumer = self._open_pipeline()
            for rowid, row in self.reader.iterrows():
                try:
                    row = consumer.consume(rowid, row)
                    if row is not None:
                        yield rowid, row
                except StopIteration:
                    break
            consumer.close()
        else:
            for rowid, row in self.reader.iterrows():
                yield rowid, row

    def insert(
        self, names: Schema, pos: Optional[int] = None,
        values: Optional[Union[Callable, Scalar, EvalFunction, List, Tuple]] = None
    ) -> DataPipeline:
        """Insert one or more columns into the rows in the data stream.

        Parameters
        ----------
        names: string, or list(string)
            Names of the inserted columns.
        pos: int, optional
            Insert position for the new columns. If None the columns will be
            appended.
        values: scalar,
                list,
                callable, or
                openclean.function.eval.base.EvalFunction, optional
            Single value, list of constant values, callable that accepts a data
            frame row as the only argument and returns a (list of) value(s)
            matching the number of columns inserted or an evaluation function
            that returns a matchin number of values.
        """
        return self.append(InsCol(names=names, pos=pos, values=values))

    def limit(self, count: int) -> DataPipeline:
        """Return a data stream for the data frame that will yield at most
        the first n rows passed to it from an associated producer.

        Parameters
        ----------
        count: int
            Maximum number of rows in the returned data frame.

        Returns
        -------
        openclean.pipeline.DataPipeline
        """
        return self.append(Limit(rows=count))

    def open(self) -> DataPipeline:
        """Return reference to self when the pipeline is opened.

        Returns
        -------
        openclean.pipeline.DataPipeline
        """
        return self

    def _open_pipeline(self) -> StreamConsumer:
        """Create stream consumer for all pipeline operators. Connect them an
        return a reference to the consumer for the first operator.

        Returns
        -------
        openclean.operator.stream.consumer.StreamConsumer
        """
        # Create a stream consumer for the first operator in the pipeline. This
        # consumer is the one that will receive all dataset rows first.
        pipeline = self.pipeline[0].open(schema=self.reader.columns)
        # Create consumer for downstream operators and connect the consumer
        # with each other. This assumes that all operaotrs (except the last
        # one) yield consumer that are also producer.
        producer = pipeline
        for op in self.pipeline[1:]:
            consumer = op.open(producer.columns)
            producer.set_consumer(consumer)
            producer = consumer
        return pipeline

    def profile(
        self, profilers: Optional[ColumnProfiler] = None,
        default_profiler: Optional[Type] = None
    ) -> List[Dict]:
        """Profile one or more columns in the data stream. Returns a list of
        profiler results for each profiled column.

        By default each column in the data stream is profiled independently
        using the default stream profiler. The optional list of profilers
        allows to override the default behavior by providing a list of column
        references (with optional profiler function). If only a column
        reference is given the default stream profiler is used for the
        referenced column.

        Parameters
        ----------
        profilers: int, string, tuple, or list of tuples of column reference
                and openclean.profiling.base.DataProfiler, default=None
            Specify he list of columns that are profiled and the profiling
            function. If only a column reference is given (not a tuple) the
            default stream profiler is used for profiling the column.
        default_profiler: class, default=None
            Class object that is instanciated as the profiler for columns
            that do not have a profiler instance speicified for them.

        Returns
        -------
        list
        """
        # Ensure that profilers is a list.
        if profilers is not None and not isinstance(profilers, list):
            profilers = [profilers]
        op = ProfileOperator(
            profilers=profilers,
            default_profiler=default_profiler
        )
        return self.stream(op)

    def run(self):
        """Stream all rows from the associated data file to the data pipeline
        that is associated with this processor. If an optional operator is
        given, that operator will be appended to the current pipeline before
        execution.

        The returned value is the result that is returned when the consumer is
        generated for the pipeline is closed after processing the data stream.

        Returns
        -------
        any
        """
        # We only need to iterate over the data stream if the pipeline has at
        # least one operator. Otherwise the instantiated pipeline does not have
        # any consumer that could generate a result.
        if not self.pipeline:
            return None
        # Create a stream consumer for the first operator in the pipeline. This
        # consumer is the one that will receive all dataset rows first.
        consumer = self._open_pipeline()
        # Stream all rows to the pipeline consumer. THe returned result is the
        # result that is returned when the consumer is closed by the reader.
        with self.reader.open() as stream:
            for rowid, row in stream:
                try:
                    consumer.consume(rowid=rowid, row=row)
                except StopIteration:
                    break
        return consumer.close()

    def select(
        self, columns: Optional[Columns] = None, names: Optional[Schema] = None
    ) -> DataPipeline:
        """Select a given list of columns from the streamed data frame. Columns
        in the resulting data stream may also be renamed using the optional
        list of new column names.

        Returns a new data stream with the column filter set to the columns
        that were in the argument list.

        Parameters
        ----------
        columns: int, str, or list of int or string, default=None
            References to the selected columns.
        names: int, str, or list of int or string, default=None
            Optional renaming for selected columns.

        Returns
        -------
        openclean.pipeline.DataPipeline
        """
        # Use the full data stream schema if no column list is given.
        if columns is None:
            columns = list(range(len(self.columns)))
        # Select the columns first.
        ds = self.append(Select(columns=columns))
        # Append an optional column rename operator if new column names are
        # given. New column names are expected to be in the same order as the
        # selected columns.
        if names is not None:
            op = Rename(columns=list(range(len(columns))), names=names)
            ds = ds.append(op)
        return ds

    def stream(self, op: StreamProcessor):
        """Stream all rows from the associated data file to the data pipeline
        that is associated with this processor. The given operator is appended
        to the current pipeline before execution.

        The returned value is the result that is returned when the consumer is
        generated for the pipeline is closed after processing the data stream.

        Parameters
        -----------
        op: openclean.operator.stream.processor.StreamProcessor
            Stream operator that is appended to the current pipeline
            for execution.

        Returns
        -------
        any
        """
        return self.append(op).run()

    def to_df(self) -> pd.DataFrame:
        """Collect all rows in the stream that are yielded by the associated
        consumer into a pandas data frame.

        Returns
        -------
        pd.DataFrame
        """
        return self.stream(DataFrame())

    def typecast(
        self, converter: Optional[DatatypeConverter] = None
    ) -> DataPipeline:
        """Typecast operator that converts cell values in data stream rows to
        different raw types that are represented by the given type converter.

        Parameters
        ----------
        converter: openclean.profiling.datatype.convert.DatatypeConverter,
                default=None
            Datatype converter for values data stream. Uses the default
            converter if no converter is given.

        Returns
        -------
        openclean.pipeline.processor.DataPipeline
        """
        return self.append(Typecast(converter=converter))

    def update(self, *args) -> DataPipeline:
        """Update rows in a data frame. Expects a list of columns that are
        updated. The last argument is expected to be an update function that
        accepts as many arguments as there are columns in the argument list.

        Raises a Value error if not enough arguments (at least two) are given.

        Parameters
        ----------
        args: list of int or string
            List of column names or index positions.

        Returns
        -------
        openclean.data.stream.processor.StreamProcessor
        """
        args = list(args)
        if len(args) < 1:
            raise ValueError('not enough arguments for update')
        return self.append(Update(columns=args[:-1], func=args[-1]))

    def where(
        self, predicate: EvalFunction, limit: Optional[int] = None
    ) -> DataPipeline:
        """Filter rows in the data stream that match a given condition. Returns
        a new data stream with a consumer that filters the rows. Currently
        expects an evaluation function as the row predicate.

        Allows to limit the number of rows in the returned data stream.

        This is a synonym for the filter() method.

        Parameters
        ----------
        predicate: opencelan.function.eval.base.EvalFunction
            Evaluation function used to filter rows.
        limit: int, default=None
            Limit the number of rows in the filtered data stream.

        Returns
        -------
        openclean.pipeline.DataPipeline
        """
        return self.filter(predicate=predicate, limit=limit)

    def write(
        self, filename: str, delim: Optional[str] = None,
        compressed: Optional[bool] = None
    ):
        """Write the rows in the data stream to a given CSV file.

        Parameters
        ----------
        filename: string
            Path to a CSV file output file on the local file system.
        delim: string, default=None
            The column delimiter used for the written CSV file.
        compressed: bool, default=None
            Flag indicating if the file contents of the created file are to be
            compressed using gzip.
        """
        file = CSVFile(
            filename=filename,
            delim=delim,
            compressed=compressed,
            write=True
        )
        return self.stream(Write(file=file))


# -- Open file or data frame as pipeline --------------------------------------

def stream(
    filename: Union[str, pd.DataFrame], header: Optional[Schema] = None,
    delim: Optional[str] = None, compressed: Optional[bool] = None
) -> DataPipeline:
    """Read a CSV file as a data stream. This is a helper method that is
    intended to read and filter large CSV files.

    Parameters
    ----------
    filename: string
        Path to CSV file on the local file system.
    header: list of string, default=None
        Optional header. If no header is given it is assumed that the first
        row in the CSV file contains the header information.
    delim: string, default=None
        The column delimiter used in the CSV file.
    compressed: bool, default=None
        Flag indicating if the file contents have been compressed using
        gzip.

    Returns
    -------
    openclean.pipeline.DataPipeline
    """
    if isinstance(filename, pd.DataFrame):
        file = DataFrameStream(df=filename)
    else:
        file = CSVFile(
            filename=filename,
            header=header,
            delim=delim,
            compressed=compressed
        )
    return DataPipeline(reader=file)