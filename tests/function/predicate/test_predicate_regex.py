# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Unit tests for regular expression match predicates for data frame rows."""

from openclean.function.predicate.regex import IsMatch, IsNotMatch


def test_predicate_regex(employees):
    """Test is match and not is match predicates."""
    # -- IsMatch --------------------------------------------------------------
    f = IsMatch(pattern='A', columns='Name')
    f.prepare(employees)
    assert f.exec(employees.iloc[0])
    assert not f.exec(employees.iloc[1])
    assert not f.exec(employees.iloc[2])
    # Full match
    f = IsMatch(pattern='A', fullmatch=True, columns='Name')
    f.prepare(employees)
    assert not f.exec(employees.iloc[0])
    assert not f.exec(employees.iloc[1])
    # -- IsNotMatch -----------------------------------------------------------
    f = IsNotMatch(pattern='A', columns='Name')
    f.prepare(employees)
    assert not f.exec(employees.iloc[0])
    assert f.exec(employees.iloc[1])
    assert f.exec(employees.iloc[2])
    # Full match
    f = IsNotMatch(pattern='A', fullmatch=True, columns='Name')
    f.prepare(employees)
    assert f.exec(employees.iloc[0])
    assert f.exec(employees.iloc[1])
    f = IsNotMatch(pattern='A.+', fullmatch=True, columns='Name')
    f.prepare(employees)
    assert not f.exec(employees.iloc[0])
    assert f.exec(employees.iloc[1])
