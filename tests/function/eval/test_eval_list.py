# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Unit tests for list evaluation functions."""

import pandas as pd
import pytest

from openclean.function.eval.base import Const
from openclean.function.eval.column import Col
from openclean.function.eval.list import Get, List


@pytest.fixture
def people():
    return pd.DataFrame(
        data=[
            ['alice davies', 23, 180],
            ['bob Smith', 33, 178]
        ],
        columns=['Name', 'Age', 'Height']
    )


def test_get_from_list():
    """Test getting a single value from a list of values generated by a tuple
    of evaluation functions.
    """
    f = Get((Const(3), Const(2), Const(1)), 2).prepare([])
    assert f.eval([]) == 1


def test_reorder_list(people):
    """Test creating a reordered list of values from a given list of values
    extracted from data frame rows by evaluation functions.
    """
    f = List([Col('Name'), Col('Age'), Col('Height')], [2, 1]).prepare(people)
    data = []
    for _, values in people.iterrows():
        data.append(f.eval(values))
    assert data == [[180, 23], [178, 33]]
