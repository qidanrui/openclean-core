# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Collection of evaluation functions that operate on string values."""

from openclean.function.eval.base import NestedEvalFunction


class Capitalize(NestedEvalFunction):
    """String function that capitalizes the first letter in argument values."""
    def __init__(self, producer, as_string=False):
        """Initialize the object properties.

        Parameters
        ----------
        producer: openclean.function.eval.base.EvalFunction
            Evaluation function to extract values from data frame rows.
        as_string: bool, optional
            Use string representation for non-string values.
        """
        super(Capitalize, self).__init__(
            func=StringFunction(
                func=str.capitalize,
                as_string=as_string,
                unpack_list=True
            ),
            producer=producer,
            is_unary=True
        )


class Concat(NestedEvalFunction):
    """String function that splits a string using a given delimiter."""
    def __init__(self, producer, delimiter, as_string=False):
        """Initialize the object properties.

        Parameters
        ----------
        producer: openclean.function.eval.base.EvalFunction
            Evaluation function to extract values from data frame rows.
        delimiter: string
            Delimiter string.
        as_string: bool, optional
            Use string representation for non-string values.
        """

        def join_string(values):
            if as_string:
                return delimiter.join([str(v) for v in values])
            else:
                return delimiter.join(values)

        super(Concat, self).__init__(
            func=join_string,
            producer=producer,
            is_unary=True
        )


class Format(NestedEvalFunction):
    """Function that returns a formated string based on a given format template
    and a variable list of input values from a data frame row.
    """
    def __init__(self, producer, template):
        """Initialize the format template and the value generation function.

        Parameters
        ----------
        producer: openclean.function.eval.base.EvalFunction
            Evaluation function to extract values from data frame rows.
        template: string
            String format template.

        Raises
        ------
        ValueError
        """

        def format_string(*args):
            return template.format(*args)

        super(Format, self).__init__(
            func=format_string,
            producer=producer,
            is_unary=False
        )


class Length(NestedEvalFunction):
    """String function that returns the length (i.e., nunumber of characters)
    for a given value.
    """
    def __init__(self, producer, as_string=False):
        """Initialize the object properties.

        Parameters
        ----------
        producer: openclean.function.eval.base.EvalFunction
            Evaluation function to extract values from data frame rows.
        as_string: bool, optional
            Use string representation for non-string values.
        """
        super(Length, self).__init__(
            func=StringFunction(
                func=len,
                as_string=as_string
            ),
            producer=producer,
            is_unary=True
        )


class Lower(NestedEvalFunction):
    """String function that converts argument values to lower case."""
    def __init__(self, producer, as_string=False):
        """Initialize the object properties.

        Parameters
        ----------
        producer: openclean.function.eval.base.EvalFunction
            Evaluation function to extract values from data frame rows.
        as_string: bool, optional
            Use string representation for non-string values.
        """
        super(Lower, self).__init__(
            func=StringFunction(
                func=str.lower,
                as_string=as_string,
                unpack_list=True
            ),
            producer=producer,
            is_unary=True
        )


class Split(NestedEvalFunction):
    """String function that splits a string using a given delimiter."""
    def __init__(self, producer, delimiter=' ', as_string=False):
        """Initialize the object properties.

        Parameters
        ----------
        producer: openclean.function.eval.base.EvalFunction
            Evaluation function to extract values from data frame rows.
        delimiter: string
            Delimiter string.
        as_string: bool, optional
            Use string representation for non-string values.
        """

        def split_string(value):
            return value.split(delimiter)

        super(Split, self).__init__(
            func=StringFunction(
                func=split_string,
                as_string=as_string
            ),
            producer=producer,
            is_unary=True
        )


class Upper(NestedEvalFunction):
    """String function that converts argument values to upper case."""
    def __init__(self, producer, as_string=False):
        """Initialize the object properties.

        Parameters
        ----------
        producer: openclean.function.eval.base.EvalFunction
            Evaluation function to extract values from data frame rows.
        as_string: bool, optional
            Use string representation for non-string values.
        """
        super(Upper, self).__init__(
            func=StringFunction(
                func=str.upper,
                as_string=as_string,
                unpack_list=True
            ),
            producer=producer,
            is_unary=True
        )


# -- Helper classes and functions ---------------------------------------------

class StringFunction(object):
    """Evaluate a given string function on a given scalar value. This class is
    a wrapper for common string functions that (i) allows to defined behavior
    for arguments that are not strings, and (ii) pass the modified value on
    to a wrapped function to compute the final result.
    """
    def __init__(self, func, as_string=False, unpack_list=False):
        """Initialize the object properties.

        Parameters
        ----------
        func: callable
            String function that is executed on given argument values.
        as_string: bool, optional
            Use string representation for non-string values.
        unpack_list: bool, default=False
            Unpack list values if set to True.
        """
        self.func = func
        self.as_string = as_string
        self.unpack_list = unpack_list

    def __call__(self, value):
        """Apply the string function on a single scalar value. Raises a
        ValueError if the value is not of type string and as_string flag is
        False.

        Parameters
        ----------
        value: scalar
            Scalar value that is tested for being a domain member.

        Returns
        -------
        scalar
        """
        if isinstance(value, list) and self.unpack_list:
            return [self(v) for v in value]
        if not isinstance(value, str):
            if self.as_string:
                return self.func(str(value))
            raise ValueError('invalid argument {}'.format(value))
        return self.func(value)
