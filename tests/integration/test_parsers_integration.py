"""Integration tests for DBC and LDF parsers

Tests the integration of:
- DBCParser + SignalInfo
- LDFParser + SignalInfo
- Parser interoperability
"""

from pathlib import Path

import pytest

from src.models.signal_model import Protocol, SignalInfo
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


def test_dbc_ldf_parsers_return_signal_info_list(sample_dbc_path, sample_ldf_path):
    """Test that both parsers return list[SignalInfo]"""
    dbc_parser = DBCParser()
    ldf_parser = LDFParser()

    dbc_signals = dbc_parser.parse(sample_dbc_path)
    ldf_signals = ldf_parser.parse(sample_ldf_path)

    assert isinstance(dbc_signals, list)
    assert isinstance(ldf_signals, list)
    assert all(isinstance(sig, SignalInfo) for sig in dbc_signals)
    assert all(isinstance(sig, SignalInfo) for sig in ldf_signals)


def test_dbc_signals_are_can_protocol(sample_dbc_path):
    """Test that DBC parser returns CAN protocol signals"""
    parser = DBCParser()
    signals = parser.parse(sample_dbc_path)

    assert len(signals) > 0
    assert all(sig.protocol == Protocol.CAN for sig in signals)


def test_ldf_signals_are_lin_protocol(sample_ldf_path):
    """Test that LDF parser returns LIN protocol signals"""
    parser = LDFParser()
    signals = parser.parse(sample_ldf_path)

    assert len(signals) > 0
    assert all(sig.protocol == Protocol.LIN for sig in signals)


def test_combined_signal_list_maintains_protocol_distinction(
    sample_dbc_path, sample_ldf_path
):
    """Test that combined signal lists maintain protocol distinction"""
    dbc_parser = DBCParser()
    ldf_parser = LDFParser()

    dbc_signals = dbc_parser.parse(sample_dbc_path)
    ldf_signals = ldf_parser.parse(sample_ldf_path)

    # Combine signals
    all_signals = dbc_signals + ldf_signals

    # Verify combined list structure
    assert len(all_signals) == len(dbc_signals) + len(ldf_signals)

    # Verify protocol counts
    can_count = sum(1 for sig in all_signals if sig.protocol == Protocol.CAN)
    lin_count = sum(1 for sig in all_signals if sig.protocol == Protocol.LIN)

    assert can_count == len(dbc_signals)
    assert lin_count == len(ldf_signals)


def test_signal_info_fields_populated_from_both_parsers(
    sample_dbc_path, sample_ldf_path
):
    """Test that SignalInfo fields are properly populated from both parsers"""
    dbc_parser = DBCParser()
    ldf_parser = LDFParser()

    dbc_signals = dbc_parser.parse(sample_dbc_path)
    ldf_signals = ldf_parser.parse(sample_ldf_path)

    # Check DBC signal fields
    for sig in dbc_signals:
        assert sig.signal_name is not None
        assert sig.message_name is not None
        assert sig.protocol == Protocol.CAN
        # min_value, max_value, unit may be None depending on DBC definition

    # Check LDF signal fields
    for sig in ldf_signals:
        assert sig.signal_name is not None
        assert sig.message_name is not None
        assert sig.protocol == Protocol.LIN


def test_parsers_handle_signal_search_consistently(sample_dbc_path, sample_ldf_path):
    """Test that signals from both parsers support search operations consistently"""
    dbc_parser = DBCParser()
    ldf_parser = LDFParser()

    dbc_signals = dbc_parser.parse(sample_dbc_path)
    ldf_signals = ldf_parser.parse(sample_ldf_path)

    # Test that all signals support matches_query
    combined = dbc_signals + ldf_signals

    # Search should work on all signals
    for sig in combined:
        # Should not raise
        sig.matches_query(sig.signal_name.lower())
        sig.matches_query("nonexistent_signal")

    # Verify at least one signal can be found
    if combined:
        first_sig = combined[0]
        matching = [s for s in combined if s.matches_query(first_sig.signal_name)]
        assert len(matching) >= 1
