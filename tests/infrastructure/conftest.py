"""
Infrastructure tests configuration - minimal imports to avoid application dependencies
"""

import pytest


# Infrastructure tests don't need database or application fixtures
# They only test static configuration files (YAML, JSON)
