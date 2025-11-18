"""
Authentication and authorization utilities
"""

from shared.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
)
from shared.auth.password import (
    hash_password,
    verify_password,
)
from shared.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    require_role,
)

__all__ = [
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "hash_password",
    "verify_password",
    "get_current_user",
    "get_current_active_user",
    "require_role",
]
