"""
Translation files directory.

This directory contains YAML translation files for supported locales:
- ru.yaml: Russian translations
- en.yaml: English translations

Translation file structure:
    _meta:
      language: "Language name"
      native_name: "Native language name"
      version: "1.0.0"
    
    category:
      subcategory:
        key: "Translated string with {variable}"
        plural_key:
          one: "Singular form"
          few: "Few form (Russian)"
          many: "Many form (Russian)"
          other: "Other/plural form"
"""

__all__ = []
