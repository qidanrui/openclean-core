# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2021 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Base class for data frame groupings. A data frame grouping splits a data
frame into multiple (potentially overlapping) data frames with the same schema.
"""

from __future__ import annotations
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Set, Tuple

import pandas as pd

from openclean.data.schema import as_list, select_clause
from openclean.data.types import Columns, Value


class DataFrameGrouping(object):
    """A data frame grouping is a mapping of key values to subsets of rows for
    a given data frame.

    Internally, this class contains a data frame and a mapping of key values to
    lists of row indices for the rows in each group. There are currently no
    restrictions on the number of groups that each of the original data frame
    rows can occur in.

    The grouping provides a basic set of methods to access the individual data
    frames that represent the different groups.
    """
    def __init__(self, df: pd.DataFrame):
        """Initialize the original data frame and the internal dictionary that
        maintains the row indices for the different groups.

        Parameters
        ----------
        df: pd.DataFrame
            Original data frame that is being grouped.
        """
        self.df = df
        self._groups = dict()

    def __iter__(self):
        """Iterate over the (key, data frame) pairs in the grouping.

        Returns
        -------
        iterable
        """
        return iter(self._groups)

    def __len__(self):
        """Get the number of groups in the grouping.

        Returns
        -------
        int
        """
        return len(self._groups)

    def add(self, key: str, rows: List[int]) -> DataFrameGrouping:
        """Add a new group to the collection. Raises a ValueError if a group
        with the given key already exists. Returns a reference to this object
        instance.

        Parameters
        ----------
        key: scalar or tuple
            Key value generated by the GroupBy operator for the rows in the
            data frame.
        rows: list(int)
            List of indices for rows in the original data frame that are
            part of the added group. Note that this is not the value for the
            index of a row in the data frame but the index into the array of
            rows i.e. the position of the row in the df.

        Returns
        -------
        openclean.data.groupby.DataFrameGrouping

        Raises
        ------
        ValueError
        """
        if key in self._groups:
            raise ValueError('duplicate key {}'.format(key))
        self._groups[key] = rows
        return self

    @property
    def columns(self) -> List[str]:
        """Get the names of columns in the schema of the grouped data frame.

        Returns
        -------
        list of string
        """
        return list(self.df.columns)

    def get(self, key: str) -> pd.DataFrame:
        """Get the data frame that is associated with the given key. Returns
        None if the given key does not exist in the grouping.

        Parameters
        ----------
        key: scalar or tuple
            Key value generated by the GroupBy operator for the rows in the
            data frame.

        Returns
        -------
        pd.DataFrame
        """
        # The result is None if no group associated with the given key.
        if key not in self._groups:
            return None
        # Create a data frame for the rows in the group.
        predicate = self.df.shape[0] * [False]
        for rowidx in self._groups[key]:
            predicate[rowidx] = True
        return self.df[predicate]

    def groups(self) -> Iterator[Tuple[str, pd.DataFrame]]:
        """Synonym for items(). Allows to iterate over the groups (and thier
        associated keys) in this grouping.

        Returns
        -------
        (scalar or tuple, pd.DataFrame)
        """
        return self.items()

    def items(self) -> Iterator[Tuple[str, pd.DataFrame]]:
        """Iterate over the groups in this grouping. Returns pairs of group
        key and the associated data frame containing the rows from the original
        data frame that are in this group.

        Returns
        -------
        (scalar or tuple, pd.DataFrame)
        """
        for key in self._groups:
            yield key, self.get(key)

    def keys(self) -> Set[str]:
        """Get set of group keys.

        Returns
        -------
        set
        """
        return set(self._groups.keys())

    def rows(self, key: str) -> List[int]:
        """Get the row indices for associated with the given key. Returns None
        if the key doesn't exist.

        Parameters
        ----------
        key : scalar or tuple
            Key values generated by the GroupBy operator for the rows in the dataframe

        Returns
        -------
        list
        """
        # The result is None if no group associated with the given key.
        if key not in self._groups:
            return None
        return self._groups[key]

    def values(self, key: str, columns: Columns) -> Counter:
        """Get values (and their frequency counts) for columns of rows in the
        group that is identified by the given key.

        Parameters
        ----------
        key: scalar or tuple
            Key value generated by the GroupBy operator for the rows in the
            data frame.
        columns: int, string, or list(int or string)
            Single column or list of column index positions or column names.

        Returns
        -------
        collections.Counter
        """
        _, colidx = select_clause(self.df.columns, columns=as_list(columns))
        # The result is None if no group is associated with the given key.
        if key not in self._groups:
            return None
        result = Counter()
        if len(colidx) == 1:
            cidx = colidx[0]
            for rowidx in self._groups[key]:
                result[self.df.iloc[rowidx][cidx]] += 1
        else:
            for rowidx in self._groups[key]:
                row = self.df.iloc[rowidx]
                key = tuple([row[cidx] for cidx in colidx])
                result[key] += 1
        return result


# -- Violation Groups ---------------------------------------------------------

@dataclass
class ValueConflicts(object):
    """Information about the number of groups and the values that a value occurs
    in as a conflicting value.
    """
    # Number of groups that the value occurs as a conflict in.
    count: int = 0
    # Values (and frequency counts) that this values occurs with in a conflict.
    values: Counter = field(default_factory=Counter)


class ConflictSummary(defaultdict):
    """Summarize conflicts in one or more attributes for groups in a data frame
    grouping.
    """
    def __init__(self):
        """Initialize the value class for the default dictionary."""
        super(ConflictSummary, self).__init__(ValueConflicts)

    def add(self, values: List[Value]):
        """Add a list of conflicting values from a data frame group.

        Parameters
        ----------
        values: list of scalar or tuple
            List of conflicting values.
        """
        for val in values:
            value_conflicts = self[val]
            value_conflicts.count += 1
            for c_val in values:
                if c_val != val:
                    value_conflicts.values[c_val] += 1

    def most_common(self, n: Optional[int] = 10) -> List[Tuple[Value, int]]:
        """Ranking of the n most common values in conflicts.

        Parameters
        ----------
        n: int, default=10
            Number of values to include in the ranking.

        Returns
        -------
        list of value and count pairs
        """
        return Counter({key: val.count for key, val in self.items()}).most_common(n)


class DataFrameViolation(DataFrameGrouping):
    """Subclass of DataFrame Grouping which maintains extra meta value
    information related to a violation.
    """
    def __init__(self, df: pd.DataFrame):
        """
        Initializes the DataFrameViolation object

        Parameters
        ----------
        df: pd.DataFrame
            the input dataframe
        """
        super(DataFrameViolation, self).__init__(df)
        self._meta = defaultdict()  # this is a dict of collections.Counter

    def get_meta(self, key: str) -> Counter:
        """Returns the counter for a key

        Parameters
        ----------
        key: str
            the key for the dataframe group
        Returns
        -------
        collections.Counter
        """
        if key not in self._meta:
            return None
        return self._meta[key]

    def add(
        self, key: str, rows: List[int], meta: Optional[Counter] = None
    ) -> DataFrameViolation:
        """Adds key:meta and key:rows to self._meta and self._groups
        respectively.

        Parameters
        ----------
        key: str
            key for the group
        rows: list
            list of indices for the group
        meta: Counter (Optional)
            meta data counters for the group

        Returns
        -------
        openclean.data.groupby.DataFrameViolation
        """
        self._meta[key] = meta
        super(DataFrameViolation, self).add(key, rows)
        return self

    def conflicts(self, key: str, columns: Columns) -> Counter:
        """Synonym to get set of values from columns in rows in a group.

        Parameters
        ----------
        key: scalar or tuple
            Key value generated by the GroupBy operator for the rows in the
            data frame.
        columns: int, string, or list(int or string)
            Single column or list of column index positions or column names.

        Returns
        -------
        collections.Counter
        """
        return self.values(key=key, columns=columns)

    def summarize_conflicts(self, columns: Columns) -> ConflictSummary:
        """Get a summary of conflicting values in one or more attributes within
        the individual groups in the grouping.

        A *conflict* is defined as a set of multiple values that occur in the
        specified column(s) within a group in this grouping. For each value
        that occurs in a conflict the summary maintains (i) the number of
        groups where the value appeared in a conflict, and (ii) a list of
        conflicting values with a count for the number of groups that these
        values conflicted in.

        Parameters
        ----------
        columns: int, string, or list(int or string)
            Single column or list of column index positions or column names.

        Returns
        -------
        openclean.data.groupby.ConflictSummary
        """
        summary = ConflictSummary()
        for key in self.keys():
            conflicts = list(self.conflicts(key=key, columns=columns).keys())
            if len(conflicts) > 1:
                summary.add(values=conflicts)
        return summary
