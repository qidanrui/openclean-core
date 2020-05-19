# This file is part of the Data Cleaning Library (openclean).
#
# Copyright (C) 2018-2020 New York University.
#
# openclean is released under the Revised BSD License. See file LICENSE for
# full license details.

"""Unit test for the downloader repositories registry."""

import pytest

from openclean.data.downloader.registry import repositories

import openclean.data.downloader.restcountries as restcountries


def test_default_registry():
    """Test the default downloader repository registry."""
    assert len(repositories()) == 1
    repo = repositories(identifier='restcountries')
    datasets = repo.datasets()
    assert len(datasets) == 1
    ds = datasets[0]
    assert ds.identifier() == restcountries.COUNTRIES
    with pytest.raises(ValueError):
        repositories(identifier='undefined')
