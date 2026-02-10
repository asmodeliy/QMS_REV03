"""
Internationalization (i18n) System

Supports multiple languages with YAML-based translation files.
Currently supports: English (en), Korean (ko)
"""

from fastapi import Request
from pathlib import Path
import yaml
from typing import Dict, Any, Optional

LOCALE_DIR = Path(__file__).parent.parent / "locales"
TRANSLATIONS: Dict[str, Dict[str, Any]] = {}
AVAILABLE_LANGUAGES = ["en", "ko"]
DEFAULT_LOCALE = "en"


def load_translations() -> None:
    """Load all translation files from locales directory"""
    global TRANSLATIONS
    
    for lang_file in LOCALE_DIR.glob("*.yml"):
        lang = lang_file.stem
        if lang not in AVAILABLE_LANGUAGES:
            continue
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                TRANSLATIONS[lang] = yaml.safe_load(f) or {}
            print(f"[OK] Loaded {lang}.yml with {len(TRANSLATIONS[lang])} keys")
        except Exception as e:
            print(f"[ERROR] Failed to load {lang}.yml: {e}")


# Load translations on module import
load_translations()


def get_locale(request: Request) -> str:
    """
    Get the user's preferred language
    
    Priority:
    1. Cookie 'lang'
    2. Accept-Language header
    3. Default: 'en'
    """
    # Check cookie first
    lang = request.cookies.get("lang")
    if lang in TRANSLATIONS:
        return lang
    
    # Check Accept-Language header
    accept_lang = request.headers.get("accept-language", "").split(",")[0].split("-")[0]
    if accept_lang in TRANSLATIONS:
        return accept_lang
    
    # Return default
    return DEFAULT_LOCALE


def t(key: str, locale: str = DEFAULT_LOCALE, **kwargs) -> str:
    """
    Get translated string
    
    Args:
        key: Translation key (dot-notation: "section.subsection.label")
        locale: Language code
        **kwargs: String formatting parameters
    
    Returns:
        Translated string or empty string if not found
    """
    if locale not in TRANSLATIONS:
        locale = DEFAULT_LOCALE
    
    # Navigate nested dictionary
    keys = key.split(".")
    value = TRANSLATIONS.get(locale, {})
    
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return ""
    
    # Return empty if not found
    if value is None:
        return ""
    
    # Format string if kwargs provided
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, ValueError):
            return value
    
    return str(value) if value else ""


def get_all_translations(locale: str = DEFAULT_LOCALE) -> Dict[str, Any]:
    """Get all translations for a specific language"""
    return TRANSLATIONS.get(locale, {})


def get_available_languages() -> list:
    """Get list of available languages"""
    return AVAILABLE_LANGUAGES


def translate_fallback(key: str, fallback: str, locale: str = DEFAULT_LOCALE) -> str:
    """
    Get translated string with fallback value
    
    Args:
        key: Translation key
        fallback: Fallback value if translation not found  
        locale: Language code
    
    Returns:
        Translated string or fallback value
    """
    result = t(key, locale)
    return result if result else fallback