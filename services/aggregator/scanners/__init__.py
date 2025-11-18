"""Scanner integration modules"""
"""Scanner implementations"""

from services.aggregator.scanners.wazuh_adapter import WazuhAdapter
from services.aggregator.scanners.mock_adapter import MockAdapter

__all__ = ["WazuhAdapter", "MockAdapter"]
