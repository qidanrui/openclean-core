# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Operators for frequency outlier detection."""

from openclean.function.list.distinct import distinct
from openclean.function.value.normalize import DivideByTotal
from openclean.profiling.anomalies.conditional import ConditionalOutliers
from openclean.profiling.helper import get_threshold


def frequency_outliers(df, columns, threshold):
    """Detect frequency outliers for values (or value combinations) in one or
    more columns of a data frame. A value (combination) is considered an
    outlier if the relative frequency satisfies the given threshold predicate.

    Parameters
    ----------
    df: pandas.DataFrame
        Input data frame.
    columns: int, string, or list(int or string)
        Single column or list of column index positions or column names.
    threshold: callable
        Function that accepts a float (i.e., the relative frequency) and that
        returns a Boolean value. True indicates that the value (frequency)
        satisfies the value outlier condition.

    Returns
    -------
    list

    Raises
    ------
    ValueError
    """
    # Create the predicate as a lookup over the normalized frequencies of
    # values in the given columns.
    values = distinct(df=df, columns=columns, normalizer=DivideByTotal())
    op = FrequencyOutliers(
        frequency=values,
        threshold=threshold
    )
    return op.find(values=values)


class FrequencyOutliers(ConditionalOutliers):
    """Detect frequency outliers for values in a given list. A value is
    considered an outlier if its relative frequency in the list satisfies the
    given threshold predicate.
    """
    def __init__(self, frequency, threshold):
        """Initialize the frequency function for list values and the threshold.

        Parameters
        ----------
        frequency: dict
            Dictionary that allows to lookup the relative frequency of a given
            value.
        threshold: callable
            Function that accepts a float (i.e., the relative frequency) and
            that returns a Boolean value. True indicates that the value
            (frequency) satisfies the value outlier condition.
        """
        super(FrequencyOutliers, self).__init__(name='frequencyOutlier')
        # If the threshold is an integer or float create a greater than
        # threshold using the value (unless the value is 1 in which case we
        # use eq).
        self.threshold = get_threshold(threshold)
        self.frequency = frequency

    def outlier(self, value):
        """Test if the relative frequency of a given value satisfies the
        outlier predicate. Returns a dictionary containing the value and
        frequency for those values that have a frequency satisfying the
        threshold and that are therefore considered outliers.
        outlier.

        Parameters
        ----------
        value: scalar or tuple
            Value that is being tested for the outlier condition.

        Returns
        -------
        bool
        """
        freq = self.frequency.get(value)
        if self.threshold(freq):
            return {'value': value, 'frequency': freq}
