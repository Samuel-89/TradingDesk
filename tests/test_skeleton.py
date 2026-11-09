"""Baseline smoke test for project initialization."""

import tradingdesk


def test_skeleton_initialization():
    """Verify package imports cleanly."""
    assert tradingdesk.__version__ == "0.1.0"
