"""
Pytest configuration for RAG tests.
"""
import pytest

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (use -m 'not slow' to skip)"
    )
