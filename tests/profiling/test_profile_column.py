# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2021 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Unit tests for the column profiler."""

from openclean.profiling.column import (
    DefaultColumnProfiler, DefaultStreamProfiler, DistinctValueProfiler
)


def test_profile_distinct_values(schools):
    """Test profiling a single data frame column using the distinct value
    profiler that maintains a full list of distinct values.
    """
    # -- Use default labels for result ----------------------------------------
    metadata = DistinctValueProfiler().run(schools, 'school_code')
    assert len(metadata.distinct()) == 96


def test_profile_single_column(schools):
    """Test profiling a single data frame column using the default profiler."""
    # -- Use default labels for result ----------------------------------------
    metadata = DefaultColumnProfiler(top_k=3).run(schools, 'grade')
    assert len(metadata['minmaxValues']) == 3
    assert metadata['minmaxValues']['int'] == {'minimum': 1, 'maximum': 8}
    assert metadata['minmaxValues']['str'] == {
        'minimum': '09-12',
        'maximum': 'MS Core'
    }
    assert metadata['totalValueCount'] == 100
    assert metadata['emptyValueCount'] == 0
    assert metadata['distinctValueCount'] == 13
    assert metadata['datatypes']['total'] == {'int': 30, 'float': 6, 'str': 64}
    assert metadata['datatypes']['distinct'] == {'int': 8, 'float': 1, 'str': 4}
    assert metadata['topValues'] == [
        ("09-12", 38),
        ("MS Core", 21),
        ("07", 8)
    ]


def test_profile_single_column_stream(schools):
    """Test profiling a data stream for a single dataset column using the
    default stream profiler.
    """
    # -- Use default labels for result ----------------------------------------
    metadata = DefaultStreamProfiler().run(schools, 'grade')
    assert len(metadata['minmaxValues']) == 3
    assert metadata['minmaxValues']['int'] == {'minimum': 1, 'maximum': 8}
    assert metadata['minmaxValues']['str'] == {
        'minimum': '09-12',
        'maximum': 'MS Core'
    }
    assert metadata['totalValueCount'] == 100
    assert metadata['emptyValueCount'] == 0
    assert metadata['datatypes']['total'] == {'int': 30, 'float': 6, 'str': 64}
