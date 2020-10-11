# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Collection of helper methods to load a dataset from CSV files."""

import pandas as pd

from typing import List, Optional, Union

from openclean.data.column import ColumnName
from openclean.data.stream.processor import StreamProcessor
from openclean.data.stream.csv import CSVFile
from openclean.data.stream.df import DataFrameStream


def dataset(
    filename: str, header: Optional[List[ColumnName]] = None,
    delim: Optional[str] = None, compressed: Optional[bool] = None
) -> pd.DataFrame:
    """Read a pandas data frame from a CSV file. This function infers the
    CSV file delimiter and compression from the file name (if not specified).
    By now the inference follows a very basic pattern. Files that have '.tsv'
    (or '.tsv.gz') as their suffix are expected to be tab-delimited. Files that
    end with '.gz' are expected to be gzip compressed.

    Returns a pandas DataFrame where the column names are instances of the
    identifiable Column class used by openclean.

    Parameters
    ----------
    filename: string
        Path to the CSV file that is being read.
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
    pd.DataFrame
    """
    file = CSVFile(
        filename=filename,
        header=header,
        delim=delim,
        compressed=compressed
    )
    with file.open() as reader:
        data, index = list(), list()
        for rowid, row in reader:
            data.append(row)
            index.append(rowid)
        return pd.DataFrame(data=data, columns=file.columns, index=index)


def stream(
    filename: Union[str, pd.DataFrame],
    header: Optional[List[ColumnName]] = None,
    delim: Optional[str] = None, compressed: Optional[bool] = None
) -> StreamProcessor:
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
    openclean.data.stream.processor.StreamProcessor
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
    return StreamProcessor(reader=file)
