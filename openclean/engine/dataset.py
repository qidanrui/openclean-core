# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2021 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""The data engine is used to manipulate a dataset with insert and update
operations that use functions from the command registry.
"""


from __future__ import annotations
from abc import ABCMeta, abstractmethod
from histore.archive.base import VolatileArchive
from histore.archive.manager.base import ArchiveManager
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from openclean.data.archive.base import ArchiveStore
from openclean.data.archive.cache import CachedDatastore
from openclean.data.archive.histore import HISTOREDatastore
from openclean.data.metadata.base import MetadataStore
from openclean.data.types import Columns, Scalar
from openclean.engine.action import CommitOp, InsertOp, OpHandle, SampleOp, UpdateOp
from openclean.engine.object.function import FunctionHandle
from openclean.engine.log import LogEntry, OperationLog
from openclean.operator.transform.insert import inscol
from openclean.operator.transform.update import update


class DatasetHandle(metaclass=ABCMeta):
    """Handle for datasets that are managed by the openclean engine and whose
    snapshot history is maintained by an archive manager.
    """
    def __init__(self, store: ArchiveStore, is_sample: bool):
        """Initialize the operation log and the flag that distinguishes dataset
        samples from full datasets.

        Parameters
        ----------
        log: openclean.engine.log.OperationLog
            Log for dataset operations.
        is_sample: bool
            Flag indicating if the dataset is a sample of a larger dataset.
        """
        self.store = store
        self.is_sample = is_sample
        self._log = OperationLog(snapshots=store.snapshots(), auto_commit=not is_sample)

    def checkout(self, identifier: Optional[str] = None) -> pd.DataFrame:
        """Checkout a dataset snapshot.

        The optional identifier references a dataset snapshot via an operation
        log entry. If no identifier is given, the snapshot for the last version
        of the dataset will be returned.

        Parameters
        ----------
        identifier: str, default=None
            Identifier for the operation log entry that represents the the
            dataset version that is being checked out.

        Returns
        -------
        pd.DataFrame
        """
        if identifier is None:
            return self.store.checkout()
        for op in self._log:
            if op.identifier == identifier:
                return self.store.checkout(version=op.version)
        raise KeyError("unknown log entry '{}'".format(identifier))

    def commit(self, df: pd.DataFrame, action: Optional[OpHandle] = None) -> pd.DataFrame:
        """Add a new snapshot to the history of the dataset.

        If no action is provided a user commit action operator is used as the
        default. Returns the data frame for the snapshot.

        Parameters
        ----------
        df: pd.DataFrame
            Data frame for the new dataset snapshot.
        action: openclean.engine.action.OpHandle, default=None
            Operator that created the dataset snapshot.

        Returns
        -------
        pd.DataFrame
        """
        action = action if action is not None else CommitOp()
        df = self.store.commit(df=df, action=action)
        # Add the operator to the internal log.
        self._log.add(version=self.store.last_version(), action=action)
        return df

    @abstractmethod
    def drop(self):
        """Delete all resources that are associated with the dataset history."""
        raise NotImplementedError()  # pragma: no cover

    def insert(
        self, names: Union[str, List[str]], pos: Optional[int] = None,
        values: Optional[Union[Scalar, FunctionHandle]] = None,
        args: Optional[Dict] = None, sources: Optional[Columns] = None
    ) -> pd.DataFrame:
        """Insert one or more columns at a given position into the dataset. One
        column is inserted for each given column name. If the insert position is
        undefined, columns are appended. If the position does not reference
        a valid position (i.e., not between 0 and len(df.columns)) a ValueError
        is raised.

        Values for the inserted columns are generated using a given constant
        value or function. If a function is given, it is expected to return
        exactly one value (e.g., a tuple of len(names)) for each of the inserted
        columns.

        Parameters
        ----------
        names: string, or list(string)
            Names of the inserted columns.
        pos: int, default=None
            Insert position for the new columns. If None, the columns will be
            appended.
        values: scalar or openclean.engine.object.func.FunctionHandle, default=None
            Single value, tuple of values, or library function that is used to
            generate the values for the inserted column(s). If no default is
            specified all columns will contain None.
        args: dict, default=None
            Additional keyword arguments that are passed to the callable together
            with the column values that are extracted from each row.
        sources: int, string, or list(int or string), default=None
            List of source columns from which the input values for the
            callable are extracted.

        Returns
        -------
        pd.DataFrame
        """
        # Checkout the current dataset snapshot.
        df = self.checkout()
        # Create an action object for the insert operation.
        action = InsertOp(
            schema=list(df.columns),
            names=names,
            pos=pos,
            values=values,
            args=args,
            sources=sources
        )
        # Run the insert operation and commit the new dataset version.
        df = inscol(df=df, names=names, pos=pos, values=action.to_eval())
        return self.commit(df=df, action=action)

    def log(self) -> List[LogEntry]:
        """Get the list of log entries for all dataset snapshots.

        Returns
        -------
        list of openclean.engine.log.LogEntry
        """
        return list(self._log)

    def metadata(self) -> MetadataStore:
        """Get metadata that is associated with the current dataset version.

        Returns
        -------
        openclean.data.metadata.base.MetadataStore
        """
        return self.store.metadata()

    def update(
        self, columns: Columns, func: FunctionHandle, args: Optional[Dict] = None,
        sources: Optional[Columns] = None
    ) -> pd.DataFrame:
        """Update a given column (or list of columns) by applying the given
        function.

        Columns defines the dataset column(s) that are being updated. If the
        given function is an evaluation function, that function will define the
        columns from which the input values are being retrieved. If the function
        is not an evaluation function, the input values for the update function
        will come from the same column(s) that are being modified. This behavior
        can be changed by specifying a list of source columns. If function is
        a callable (not an evaluation function) and sources is given, row values
        from the column(s) that are specified by `sounrces` are used as the input
        to the update function.

        Parameters
        ----------
        columns: int, string, or list(int or string)
            Single column or list of column index positions or column names.
        func: openclean.engine.object.func.FunctionHandle
            Library function that is used to generate modified values for the
            updated column(s).
        args: dict, default=None
            Additional keyword arguments that are passed to the callable together
            with the column values that are extracted from each row.
        sources: int, string, or list(int or string), default=None
            List of source columns from which the input values for the
            callable are extracted.

        -------
        pd.DataFrame
        """
        # Checkout the current dataset snapshot.
        df = self.checkout()
        # Create an action object for the update operation.
        action = UpdateOp(
            schema=list(df.columns),
            columns=columns,
            func=func,
            args=args,
            sources=sources
        )
        # Run the update operation and commit the new dataset version.
        df = update(df=df, columns=columns, func=action.to_eval())
        return self.commit(df=df, action=action)

    def version(self) -> int:
        """Get version identifier for the last snapshot of the dataset.

        Returns
        -------
        int
        """
        return self._log.last_version()


class FullDataset(DatasetHandle):
    """Handle for datasets that are managed by the openclean engine and that
    have their history being maintained by an archive manager. All operations
    are applied directly on the full dataset in the underlying archive.
    """
    def __init__(
        self, datastore: ArchiveStore, manager: ArchiveManager, identifier: str,
        pk: Optional[Union[List[str], str]] = None
    ):
        """Initialize the reference to the datastore that maintains the history
        of the dataset that is being tranformed.

        Parameters
        ----------
        datastore: openclean.data.archive.base.ArchiveStore
            Datastore for managing dataset snapshots.
        manager: histore.archive.manager.base.ArchiveManager
            Manager for created dataset archives.
        identifier: string, default=None
            Unique identifier of the dataset archive. The identifier is used
            to access the dataset history in the archive manager.
        pk: string or list, default=None
            Column(s) that define the primary key for the dataset. This
            information is accessed when generating a sample of the dataset
            (by the data engine).
        """
        super(FullDataset, self).__init__(store=datastore, is_sample=False)
        self.manager = manager
        self.identifier = identifier
        self.pk = pk

    def drop(self):
        """Delete all resources that are associated with the dataset history."""
        self.manager.delete(self.identifier)


class DataSample(DatasetHandle):
    """Handle for datasets that are samples of a larger dataset. Samples datasets
    are entirely maintained in main memory.

    This class maintains a reference to the orginal sample and the to the current
    modified version of the sample. If intermediate versions need to be accessed
    they will be recreated by re-applying the sequence of operations that generated
    them.

    The class also has a reference to the handle for the full dataset.
    """
    def __init__(
        self, df: pd.DataFrame, original: DatasetHandle, n: int,
        random_state: Optional[Tuple[int, List]] = None
    ):
        """Initialize the reference to the data sample and the handle for the
        original (full) dataset.

        Parameters
        ----------
        df: pd.DataFrame
            Data frame for the dataset sample.
        original: openclean.engine.dataset.DatasetHandle
            Reference to the original dataset for sampled datasets.
        n: int
            Number of rows in the sample dataset.
        random_state: int or list, default=None
            Seed for random number generator.
        """
        archive = VolatileArchive()
        store = CachedDatastore(datastore=HISTOREDatastore(archive))
        store.commit(df, action=SampleOp(args={'n': n, 'randomState': random_state}))
        super(DataSample, self).__init__(store=store, is_sample=True)
        self.original = original

    def drop(self):
        """Delete all resources that are associated with the dataset history."""
        self.original.drop()

    def rollback(self, identifier: str) -> pd.DataFrame:
        """Rollback to the dataset version that was created by the log entry
        before the entry with the given identifier. That is, we rollback all
        changes that occurred by the identified operation and all following
        ones. This will make the respective snapshot of the previous entry in
        the operation log the new current (head) snapshot for the dataset
        history.

        Rollback is only supported for uncommitted changes. Removes all log
        entries starting from the rollback version.

        Returns the dataframe for the dataset snapshot that is at the new head
        of the dataset history.

        Raises a KeyError if the given log entry identifier is unknown. Raises
        a ValueError if the log entry references a snapshot that has already
        been committed.

        Parameters
        ----------
        identifier: string
            Unique log entry identifier.

        Returns
        -------
        pd.DataFrame
        """
        pos = 0
        for op in self.log():
            pos += 1
            if op.identifier == identifier:
                if op.is_committed:
                    raise ValueError('can only rollback uncommitted actions')
                # Remove all log entries starting from the rollback position.
                self._log.truncate(pos)
                self.store.rollback(version=op.version)
                return self.checkout()
        # Raise a KeyError if no log entry with the given identifier was found.
        raise KeyError("unknown snapshot '{}'".format(identifier))


# -- Helper Methods -----------------------------------------------------------

def exec_operations(
    df: pd.DataFrame, operations: List[OpHandle], datastore: Optional[ArchiveStore] = None
) -> pd.DataFrame:
    """Re-apply a sequence of operators on a given dataframe. If the datastore
    for the original dataset is given the changes will be commited.

    Parameters
    ----------
    df: pd.DataFrame
        Data frame for original datataset snapshot.
    operations: list of openclean.engine.action.OpHandle
        List of operations that are being appiled.
    datastore: openclean.data.archive.base.ArchiveStore, default=None
        Optional datastore for the full dataset.

    Returns
    -------
    pd.DataFrame
    """
    for op in operations:
        # Execute the operation on the latest snapshot of the original
        # dataset and commit the modified snapshot to that dataset.
        action = op.action
        if action.is_insert:
            df = inscol(
                df=df,
                names=action.names,
                pos=action.pos,
                values=action.to_eval()
            )
        elif action.is_update:
            df = update(df=df, columns=action.columns, func=action.to_eval())
        else:
            raise RuntimeError("cannot re-apply '{}' action".format(op.optype))
        # Commit the dataset (only if the datastore for the full dataset is
        # given).
        if datastore is not None:
            df = datastore.commit(df=df, action=action)
            op.is_committed = True
    return df
