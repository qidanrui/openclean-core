# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Class that implements the DataframeMapper abstract class to perform groupby
operations on a pandas dataframe.
"""

from openclean.data.groupby import DataFrameGrouping
from openclean.operator.base import DataFrameMapper
from openclean.function.eval.base import Cols, EvalFunction, Eval


def groupby(df, columns, func=None, having=None):
    """Groupby function for data frames. Evaluates a new index based on the
    rows of the dataframe using the input function (optional). The output
    comprises of a openclean.data.groupby.DataFrameGrouping object.


    Parameters
    ----------
    df: pandas.DataFrame
        Input data frame.
    columns: int, string, or list(int or string), optional
        Single column or list of column index positions or column names.
    func: (
            openclean.function.eval.base.EvalFunction,
            openclean.function.eval.base.value.ValueFunction,
            callable,
        )
        Evaluation function or callable that accepts a data frame row as the
        only argument (if columns is None). ValueFunction or callable if one
        or more columns are specified.
    having: int or callable (default: None)
        If given, group by only returns groups that (i) have a number of rows that equals a given int or
        (ii) (if a callable is given) we pass the group to that callable as an argument and if
        the returned result is True the group is included in the returned result.
        The callable should expect a pandas dataframe and return a boolean

    Returns
    -------
    openclean.data.groupby.DataFrameGrouping
    """
    gpby = GroupBy(columns=columns, func=func)
    all_groups = gpby.map(df=df)

    if having is not None:
        selected_groups = DataFrameGrouping(df=df)
        for key, group in all_groups.groups():
            if GroupBy.select(group, having):
                selected_groups.add(key=key, rows=list(group.index))
    else:
        selected_groups = all_groups

    return selected_groups


class GroupBy(DataFrameMapper):
    """GroupBy class that takes in the column names to group on and a function
    (optional), performs the groupby and returns a DataFrameGrouping object.
    """
    def __init__(self, columns, func=None):
        """Initialize the column names and an optional function.

        Parameters
        ----------
        columns: list or string
            The column names to group by on
        func: callable
            The new index generator function
        """
        super(GroupBy, self).__init__()
        self.func = get_eval_func(columns=columns, func=func)

    def _transform(self, df):
        """Applies the groupby function and returns a dict of groups.

        Parameters
        ----------
        df: pandas.DataFrame
            Dataframe to transform using groupby

        Returns
        _______
        dict
        """
        prepared = self.func.prepare(df=df)
        groups = dict()
        for index, rows in df.iterrows():
            value = prepared.eval(rows)
            if isinstance(value, list):
                value = tuple(value)
            if value not in groups:
                groups[value] = list()
            groups[value].append(index)

        return groups

    def map(self, df):
        """transforms and maps a pandas DataFrame into a DataFrameGrouping object.

        Parameters
        ----------
        df: pandas.DataFrame
            Dataframe to transform using groupby

        Returns
        _______
        openclean.data.groupby.DataFrameGrouping
        """
        # unpack any user set indices to default pandas representations
        df_reindexed = df.reset_index() if df.index.duplicated().any() or df.index.dtype != int else df  # noqa: E501
        groupedby = self._transform(df=df_reindexed)
        grouping = DataFrameGrouping(df=df_reindexed)
        for gby in groupedby:
            grouping.add(key=gby, rows=groupedby[gby])
        return grouping

    @staticmethod
    def select(group, condition):
        """
        Given a dataframe and a condition, returns a bool of whether the group should be selected

        Parameters
        ----------
        group: pd.DataFrame
            the group/df under consideration
        condition: int or callable
            if not provided, the group is selected
            if int, the group's number of rows is checked against the condition
            if callable, the group is passed to it. The callable should return a boolean

        Returns
        -------
        bool

        Raises
        ------
        TypeError
        """
        if condition is None:
            return True
        elif isinstance(condition, int):
            return group.shape[0] == condition
        elif callable(condition):
            if not isinstance(condition(group), bool):
                raise TypeError('selection condition expected to return a boolean')
            return condition(group)
        return False


# -- Helper Methods -----------------------------------------------------------
def get_eval_func(columns=None, func=None):
    """Helper method used to evaluate a func on data frame rows.

    Parameters
    ----------
    columns: int, string, or list(int or string), optional
        Single column or list of column index positions or column names.
    func: (
            openclean.function.eval.base.EvalFunction,
            openclean.function.eval.base.value.ValueFunction,
            callable,
        )
        Evaluation function or callable that accepts a data frame row as the
        only argument (if columns is None). ValueFunction or callable if one
        or more columns are specified.

    Returns
    -------
    openclean.function.eval.base.EvalFunction

    Raises
    ------
    ValueError
    """
    # If columns is a callable or eval function and func is None we
    # flip the columns and func values.
    if func is None and columns is not None:
        if isinstance(columns, EvalFunction):
            func = columns
            columns = None
        else:
            columns = [columns] if not isinstance(columns, list) else columns
            func = Cols(*columns)

    # If one or more columns and func both are specified
    elif columns is not None:
        # Ensure that columns is a list.
        if not isinstance(columns, list):
            columns = [columns]
        # Convert func to an evaluation function.
        if callable(func):
            func = Eval(func=func, columns=columns)

    elif not isinstance(func, EvalFunction):
        func = Eval(func=func, columns=columns)

    # Raise a ValueError if function isnt recognized found.
    if func is None:
        raise ValueError('func not acceptable')

    return func