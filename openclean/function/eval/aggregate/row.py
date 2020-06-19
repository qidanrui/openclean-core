# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Collection of evaluation functions that compute a result over a list of
values that are extracted for data frame rows.
"""

import numpy as np

from openclean.function.eval.base import EvalFunction
from openclean.function.eval.column import Col


# -- Generic function for lists of values -------------------------------------

class RowCellsFunction(EvalFunction):
    """The list of values function evaluates a given function (callable) on a
    list of values extracted from different cells in the same data frame row
    using evaluation functions.

    This function allows, for example, to compute the minimum or maximum over
    values from different columns in a data frame row.
    """
    def __init__(self, aggregator, values):
        """Initialize the callable and the list of evaluation functions that
        are used to extract values that are used as arguments for the list
        function.

        Parameters
        ----------
        aggregator: callable
            Function that accepts a list of values as input.
        values: list(openclean.function.eval.base.EvalFunction)
            List of evaluation functions that are used to generate the inputs
            for the list function (e.g., extract values from columns in a data
            frame row).
        """
        self.aggregator = aggregator
        self.values = values if isinstance(values, list) else [values]

    def eval(self, values):
        """Evaluate the value functions on the data frame row. The collected
        results are then passed to the list function to compute the return
        value for this function.

        Parameters
        ----------
        values: pandas.core.series.Series
            Row in a pandas data frame.

        Returns
        -------
        scalar
        """
        return self.aggregator([f.eval(values) for f in self.values])

    def prepare(self, df):
        """Prepare the associated evaluation functions.

        Parameters
        ----------
        df: pandas.DataFrame
            Input data frame.

        Returns
        -------
        openclean.function.eval.base.EvalFunction
        """
        for f in self.values:
            f.prepare(df)
        return self


# -- Shortcuts for common list functions --------------------------------------

class Max(RowCellsFunction):
    """Evaluation function that returns the maximum value for a list of values
    from different cells in a data frame row.
    """
    def __init__(self, *args):
        """Initialize the statistics function in the super class as well as the
        list of values (e.g., columns) on which the function will be applied.

        Parameters
        ----------
        args: list(string, or openclean.function.eval.base.EvalFunction)
            List of evaluation functions that are used to generate the inputs
            for the list function (e.g., extract values from columns in a data
            frame row).
        """
        values = [colfunc(arg) for arg in args]
        super(Max, self).__init__(aggregator=max, values=values)


class Mean(RowCellsFunction):
    """Evaluation function that returns the mean of values for one or more
    columns in a data frame as the result value for all columns in the data
    frame.
    """
    def __init__(self, *args):
        """Initialize the statistics function in the super class as well as the
        list of values (e.g., columns) on which the function will be applied.

        Parameters
        ----------
        args: list(string, or openclean.function.eval.base.EvalFunction)
            List of evaluation functions that are used to generate the inputs
            for the list function (e.g., extract values from columns in a data
            frame row).
        """
        values = [colfunc(arg) for arg in args]
        super(Mean, self).__init__(aggregator=np.mean, values=values)


class Min(RowCellsFunction):
    """Evaluation function that returns the minimum of values for one or more
    columns in a data frame as the result value for all columns in the data
    frame.
    """
    def __init__(self, *args):
        """Initialize the statistics function in the super class as well as the
        list of values (e.g., columns) on which the function will be applied.

        Parameters
        ----------
        args: list(string, or openclean.function.eval.base.EvalFunction)
            List of evaluation functions that are used to generate the inputs
            for the list function (e.g., extract values from columns in a data
            frame row).
        """
        values = [colfunc(arg) for arg in args]
        super(Min, self).__init__(aggregator=min, values=values)


class Sum(RowCellsFunction):
    """Evaluation function that returns the sum of values for one or more
    column in a data frame as the result value for all rows in the data
    frame.
    """
    def __init__(self, *args):
        """Initialize the statistics function in the super class as well as the
        list of values (e.g., columns) on which the function will be applied.

        Parameters
        ----------
        args: list(string, or openclean.function.eval.base.EvalFunction)
            List of evaluation functions that are used to generate the inputs
            for the list function (e.g., extract values from columns in a data
            frame row).
        """
        values = [colfunc(arg) for arg in args]
        super(Sum, self).__init__(aggregator=sum, values=values)


# -- Helper Methods -----------------------------------------------------------

def colfunc(func):
    """Ensure that the argument is an evaluation function. If the value is a
    string it is assumed to be a column name and a column function is returned.

    Returns
    -------
    openclean.function.eval.base.EvalFunction
    """
    if not isinstance(func, EvalFunction):
        if isinstance(func, str):
            return Col(func)
        raise ValueError("invalid argument '{}'".format(func))
    return func
