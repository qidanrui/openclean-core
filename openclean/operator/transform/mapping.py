# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Transformation operator that returns a new data frame containing a mapping
of original values in a data frame to values that are the result of applying an
update function on the original values. The resulting data frame is considered
a representation of the effect of applying an update function on a given data
frame.
"""

import pandas as pd

from openclean.data.column import as_list, select_clause
from openclean.operator.base import DataFrameTransformer
from openclean.operator.transform.update import get_update_function


# -- Functions ----------------------------------------------------------------

def mapping(df, columns, func, names=None):
    """Get the mapping of values that are modified by an update function.

    Parameters
    ----------
    df: pandas.DataFrame
        Input data frame.
    columns: int, string, or list(int or string), optional
        Single column or list of column index positions or column names.
    func: callable or openclean.function.base.EvalFunction
        Callable that accepts a data frame row as the only argument and outputs
        a (modified) list of value(s).
    names: list(string)
        List of names for the columns of the resulting data frame.

    Returns
    -------
    pandas.DataFrame

    Raises
    ------
    ValueError
    """
    return Mapping(columns=columns, func=func, names=names).transform(df)


# -- Operators ----------------------------------------------------------------

class Mapping(DataFrameTransformer):
    """Data frame transformer that generates a new data frame containing a
    mapping of original values from columns in a given data frame that are
    mapped to the results of applying a given update funtion. The result thus
    represents the effect of applying an update function to a given data frame.
    """
    def __init__(self, columns, func, names=None):
        """Initialize the list of updated columns, the update function, and the
        optional list of names for the columns in the resulting data frame. If
        the list of column names is not given, names for columns containing
        original values will be named 'source' and columns containing results
        of applying the update function will be named 'target'. If there are
        multiple source or target columns the column names will have an index
        appended (starting at 0).

        Parameters
        ----------
        columns: int, string, or list(int or string), optional
            Single column or list of column index positions or column names.
        func: callable or openclean.function.base.EvalFunction
            Callable that accepts a data frame row as the only argument and
            outputs a (modified) (list of) value(s).
        names: list(string), default=None
            List of names for the columns of the resulting data frame.

        Raises
        ------
        ValueError
        """
        # Ensure that columns is a list
        self.columns = as_list(columns)
        self.func = get_update_function(func=func, columns=self.columns)
        self.names = names

    def transform(self, df):
        """Generate new data frame by applying the update function to rows in
        the given data frame. The rows in the resulting data frame are composed
        of the original column values and the resulting values returned by the
        update function.

        Parameters
        ----------
        df: pandas.DataFrame
            Input data frame.

        Returns
        -------
        pandas.DataFrame
        """
        # Get list of indices for source columns.
        _, colidxs = select_clause(df=df, columns=self.columns)
        # Call the prepare method of the update function.
        self.func.prepare(df)
        # Create a modified data frame where rows are modified by the update
        # function.
        mapping = dict()
        # Have different implementations for single column or multi-column
        # updates.
        if len(colidxs) == 1:
            colidx = colidxs[0]
            for _, values in df.iterrows():
                val = self.func(values)
                mapping[values[colidx]] = val
        else:
            for _, values in df.iterrows():
                vals = self.func(values)
                mapping[tuple([values[i] for i in colidxs])] = vals
        # Create a data frame for the mapping dictionary.
        data = list()
        for key in mapping:
            if len(colidxs) == 1:
                row = [key]
            else:
                row = list(key)
            val = mapping[key]
            if isinstance(val, tuple):
                row.extend(list(val))
            else:
                row.append(val)
            data.append(row)
            target_cols = len(row) - len(colidxs)
        if self.names is not None:
            columns = self.names
        else:
            if len(colidxs) > 1:
                columns = ['source{}'.format(i) for i in range(len(colidxs))]
            else:
                columns = ['source']
            if target_cols > 1:
                tcols = ['target{}'.format(i) for i in range(target_cols)]
                columns.extend(tcols)
            else:
                columns.append('target')
        return pd.DataFrame(data=data, columns=columns)
