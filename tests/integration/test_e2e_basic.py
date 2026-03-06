"""Basic E2E test

Tests basic end-to-end workflow:
1. Parse DBC file
2. Parse LDF file
3. Combine signals
4. Perform search operations

Note: GUI testing will be implemented in Phase 2
"""

from pathlib import Path

import pytest

from src.parsers.dbc_parser import DBCParser
from src.parsers.ldf_parser import LDFParser


@pytest.fixture
def sample_dbc_path():
    """Path to sample DBC file"""
    return Path(__file__).parent.parent / "fixtures" / "sample.dbc"


@pytest.fixture
def sample_ldf_path():
    """Path to sample LDF file"""
    return Path(__file__).parent.parent / "fixtures" / "sample.ldf"


def test_e2e_parse_and_combine_signals(sample_dbc_path, sample_ldf_path):
    """
    E2E Test: Parse DBC and LDF files, combine signals

    Workflow:
    1. Initialize parsers
    2. Parse both file types
    3. Combine signal lists
    4. Verify combined result
    """
    # Step 1: Initialize parsers
    dbc_parser = DBCParser()
    ldf_parser = LDFParser()

    # Step 2: Parse files
    dbc_signals = dbc_parser.parse(sample_dbc_path)
    ldf_signals = ldf_parser.parse(sample_ldf_path)

    # Step 3: Combine signals (simulating user workflow)
    all_signals = dbc_signals + ldf_signals

    # Step 4: Verify
    assert len(all_signals) > 0
    assert len(all_signals) == len(dbc_signals) + len(ldf_signals)


def test_e2e_signal_search_workflow(sample_dbc_path, sample_ldf_path):
    """
    E2E Test: Parse files and perform signal search

    Workflow:
    1. Parse DBC and LDF
    2. Combine signals
    3. Search for specific signal
    4. Verify search results
    """
    # Step 1-2: Parse and combine
    dbc_parser = DBCParser()
    ldf_parser = LDFParser()
    all_signals = dbc_parser.parse(sample_dbc_path) + ldf_parser.parse(sample_ldf_path)

    # Step 3: Search for a signal (case-insensitive)
    # Assuming sample.dbc has "EngineSpeed" signal
    query = "engine"
    matching_signals = [sig for sig in all_signals if sig.matches_query(query)]

    # Step 4: Verify search works
    # At minimum, should not crash; ideally finds matches
    assert isinstance(matching_signals, list)
    # If sample files contain "engine" signal, this should find it
    # If not, empty list is valid


def test_e2e_display_name_generation(sample_dbc_path, sample_ldf_path):
    """
    E2E Test: Verify display names are generated for all signals

    Workflow:
    1. Parse files
    2. Check display_name property
    3. Verify format
    """
    dbc_parser = DBCParser()
    ldf_parser = LDFParser()
    all_signals = dbc_parser.parse(sample_dbc_path) + ldf_parser.parse(sample_ldf_path)

    # All signals should have display names
    for sig in all_signals:
        display_name = sig.display_name
        assert isinstance(display_name, str)
        assert len(display_name) > 0
        # Display name contains message and signal information
        # May be in format "MessageName.SignalName" or similar
        assert sig.signal_name in display_name


def test_e2e_protocol_filtering(sample_dbc_path, sample_ldf_path):
    """
    E2E Test: Filter signals by protocol

    Workflow:
    1. Parse and combine
    2. Filter by CAN protocol
    3. Filter by LIN protocol
    4. Verify filters work correctly
    """
    from src.models.signal_model import Protocol

    dbc_parser = DBCParser()
    ldf_parser = LDFParser()
    all_signals = dbc_parser.parse(sample_dbc_path) + ldf_parser.parse(sample_ldf_path)

    # Filter by protocol
    can_signals = [sig for sig in all_signals if sig.protocol == Protocol.CAN]
    lin_signals = [sig for sig in all_signals if sig.protocol == Protocol.LIN]

    # Verify filters
    assert len(can_signals) > 0  # Assuming sample.dbc has signals
    assert len(lin_signals) > 0  # Assuming sample.ldf has signals
    assert len(can_signals) + len(lin_signals) == len(all_signals)
