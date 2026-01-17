"""Secure API key storage using system keyring.

Falls back to environment variables if keyring is unavailable.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = "math-digitizer"

# Try to import keyring, but don't fail if unavailable
_keyring_available = False
try:
    import keyring
    from keyring.errors import KeyringError
    _keyring_available = True
except ImportError:
    keyring = None  # type: ignore
    KeyringError = Exception  # type: ignore


class SecretKey(str, Enum):
    """Known API key identifiers."""
    
    GEMINI = "gemini_api_key"
    DASHSCOPE = "dashscope_api_key"
    DEEPSEEK_MODELVERSE = "deepseek_modelverse_api_key"
    DEEPSEEK_SILICONFLOW = "deepseek_siliconflow_api_key"
    DEEPSEEK_CUSTOM = "deepseek_custom_api_key"
    
    @classmethod
    def for_provider(cls, provider: str) -> "SecretKey":
        """Get the secret key enum for a DeepSeek provider."""
        mapping = {
            "modelverse": cls.DEEPSEEK_MODELVERSE,
            "siliconflow": cls.DEEPSEEK_SILICONFLOW,
            "custom": cls.DEEPSEEK_CUSTOM,
        }
        return mapping.get(provider.lower(), cls.DEEPSEEK_MODELVERSE)


# Environment variable fallback mapping
_ENV_VAR_MAPPING: dict[SecretKey, list[str]] = {
    SecretKey.GEMINI: ["GEMINI_API_KEY"],
    SecretKey.DASHSCOPE: ["DASHSCOPE_API_KEY"],
    SecretKey.DEEPSEEK_MODELVERSE: ["MODELVERSE_API_KEY", "DEEPSEEK_API_KEY"],
    SecretKey.DEEPSEEK_SILICONFLOW: ["SILICONFLOW_API_KEY"],
    SecretKey.DEEPSEEK_CUSTOM: ["DEEPSEEK_API_KEY", "MODELVERSE_API_KEY", "SILICONFLOW_API_KEY"],
}


def _get_from_env(key: SecretKey) -> Optional[str]:
    """Get API key from environment variables."""
    env_vars = _ENV_VAR_MAPPING.get(key, [])
    for var in env_vars:
        if value := os.environ.get(var, "").strip():
            return value
    return None


def get_api_key(key: SecretKey | str) -> Optional[str]:
    """Get an API key from secure storage.
    
    Lookup order:
    1. System keyring (if available)
    2. Environment variables
    
    Args:
        key: SecretKey enum or string identifier
        
    Returns:
        The API key value or None if not found
    """
    if isinstance(key, str):
        try:
            key = SecretKey(key)
        except ValueError:
            # Unknown key, just try keyring/env directly
            pass
    
    # Try keyring first
    if _keyring_available and keyring is not None:
        try:
            key_name = key.value if isinstance(key, SecretKey) else key
            value = keyring.get_password(SERVICE_NAME, key_name)
            if value:
                return value
        except KeyringError as e:
            logger.debug(f"Keyring lookup failed for {key}: {e}")
    
    # Fall back to environment
    if isinstance(key, SecretKey):
        return _get_from_env(key)
    
    return None


def set_api_key(key: SecretKey | str, value: str) -> bool:
    """Store an API key in secure storage.
    
    Args:
        key: SecretKey enum or string identifier
        value: The API key value to store
        
    Returns:
        True if stored successfully, False otherwise
    """
    if not _keyring_available or keyring is None:
        logger.warning("Keyring not available, cannot store API key securely")
        return False
    
    try:
        key_name = key.value if isinstance(key, SecretKey) else key
        keyring.set_password(SERVICE_NAME, key_name, value)
        logger.info(f"Stored API key: {key_name}")
        return True
    except KeyringError as e:
        logger.error(f"Failed to store API key {key}: {e}")
        return False


def delete_api_key(key: SecretKey | str) -> bool:
    """Delete an API key from secure storage.
    
    Args:
        key: SecretKey enum or string identifier
        
    Returns:
        True if deleted successfully, False otherwise
    """
    if not _keyring_available or keyring is None:
        return False
    
    try:
        key_name = key.value if isinstance(key, SecretKey) else key
        keyring.delete_password(SERVICE_NAME, key_name)
        logger.info(f"Deleted API key: {key_name}")
        return True
    except KeyringError as e:
        logger.debug(f"Failed to delete API key {key}: {e}")
        return False


def list_api_keys() -> dict[str, bool]:
    """List all known API keys and their availability.
    
    Returns:
        Dict mapping key names to whether they have a value set
    """
    result = {}
    for key in SecretKey:
        result[key.value] = get_api_key(key) is not None
    return result


def is_keyring_available() -> bool:
    """Check if system keyring is available."""
    return _keyring_available
