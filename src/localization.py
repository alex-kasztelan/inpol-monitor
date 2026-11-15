"""Localization module for Inpol Monitor.

Loads language bundles from JSON files based on LANGUAGE environment variable.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default language
DEFAULT_LANGUAGE = "en"

# Cache for loaded translations
_translations: Dict[str, Any] = {}


def set_language(lang: str):
    """Set the current language (for session-based switching).
    
    Args:
        lang: Language code (en, pl, ru, ua)
    """
    global _current_language
    _current_language = lang


def get_language() -> str:
    """Get current language setting.
    
    Returns:
        Language code (en, pl, ru, ua)
    """
    return os.getenv("LANGUAGE", DEFAULT_LANGUAGE)


def load_translations(language: str = None) -> Dict[str, Any]:
    """Load translations for specified language.
    
    Args:
        language: Language code (en, pl, ru, ua). If None, uses get_language().
    
    Returns:
        Translation dictionary
    
    Raises:
        FileNotFoundError: If language bundle not found
    """
    lang = language or get_language()
    
    # Always reload when language is passed explicitly (don't use cache)
    if language is not None:
        _translations.pop(language, None)
    
    if lang in _translations:
        return _translations[lang]
    
    # Find the JSON file
    base_path = Path(__file__).parent.parent
    json_path = base_path / f"{lang}.json"
    
    if not json_path.exists():
        # Try project root
        json_path = base_path.parent / f"{lang}.json"
    
    if not json_path.exists():
        logger.error(f"Language bundle not found: {lang}.json")
        raise FileNotFoundError(f"Language bundle not found: {lang}.json")
    
    with open(json_path, "r", encoding="utf-8-sig") as f:
        _translations[lang] = json.load(f)
    
    logger.info(f"Loaded translations for language: {lang}")
    return _translations[lang]


def t(key: str, default: str = None, language: str = None) -> str:
    """Get translated string by key.
    
    Supports nested keys with dot notation, e.g., "Cases.Title"
    
    Args:
        key: Translation key (dot-separated path)
        default: Default value if key not found
        language: Language code (uses session language if in Flask context)
    
    Returns:
        Translated string or default/.key if not found
    """
    translations = load_translations(language)
    
    # Navigate nested structure
    parts = key.split(".")
    value = translations
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            result = default if default is not None else f"[{key}]"
            logger.debug(f"Translation key not found: {key}")
            return result
    
    return value if isinstance(value, str) else str(value)


def get_status_label(status_id: str) -> str:
    """Get status label for status ID.
    
    Args:
        status_id: Status ID (numeric string like "1", "2", etc.)
    
    Returns:
        Localized status label
    """
    return t(f"Cases.States.{status_id}", f"Unknown ({status_id})")


def get_question_title(title_id: str) -> str:
    """Get question title for title ID.
    
    Args:
        title_id: Question title ID (numeric string like "1", "2", etc.)
    
    Returns:
        Localized question title
    """
    return t(f"Cases.Question.Titles.{title_id}", f"Unknown ({title_id})")


def get_question_status(status_id: str) -> str:
    """Get question status label for status ID.
    
    Args:
        status_id: Status ID (numeric string like "1", "2", etc.)
    
    Returns:
        Localized question status
    """
    return t(f"Cases.Question.Statuses.{status_id}", f"Unknown ({status_id})")


def get_file_type(file_type_id: str) -> str:
    """Get file type label for file type ID.
    
    Args:
        file_type_id: File type ID (numeric string like "1", "2", etc.)
    
    Returns:
        Localized file type
    """
    return t(f"Files.Types.{file_type_id}", f"Unknown ({file_type_id})")


# Pre-load translations on module import
try:
    load_translations()
except Exception as e:
    logger.warning(f"Failed to load translations on import: {e}")