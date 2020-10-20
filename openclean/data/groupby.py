# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.
from collections import defaultdict

"""Base class for data frame groupings. A data frame grouping splits a data
frame into multiple (potentially overlapping) data frames with the same schema.
"""


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
    def __init__(self, df):
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

    def add(self, key, rows):
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
            rows.

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

    def get(self, key):
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
        return self.df.loc[self.df.index.isin(self._groups[key])]

    def groups(self):
        """Synonym for items(). Allows to iterate over the groups (and thier
        associated keys) in this grouping.

        Returns
        -------
        (scalar or tuple, pd.DataFrame)
        """
        return self.items()

    def items(self):
        """Iterate over the groups in this grouping. Returns pairs of group
        key and the associated data frame containing the rows from the original
        data frame that are in this group.

        Returns
        -------
        (scalar or tuple, pd.DataFrame)
        """
        for key in self._groups:
            yield key, self.get(key)

    def keys(self):
        """Get set of group keys.

        Returns
        -------
        set
        """
        return set(self._groups.keys())


class DataFrameViolation(DataFrameGrouping):
    """Subclass of DataFrame Grouping which maintains extra meta value information related to a violation
    """
    def __init__(self, df, lhs, rhs):
        """
        Initializes the DataFrameViolation object

        Parameters
        ----------
        df: pd.DataFrame
            the input dataframe
        lhs: list or str
            the left hand side of the violation operation / determinant column(s)
        rhs: list or str
            the right side of the violation operaion / dependant column(s)
        """
        super(DataFrameViolation, self).__init__(df)
        self._meta = defaultdict() # this is a dict of collections.Counter
        self._lhs = lhs
        self._rhs = rhs

    def get_meta(self, key):
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

    def add(self, key, rows, meta=None):
        """Adds key:meta and key:rows to self._meta and self._groups respectively

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
        return super(DataFrameViolation, self).add(key, rows)
