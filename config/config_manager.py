"""
Configuration manager for Python Style Converter.
Handles loading, validation, and management of configuration settings.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from jsonschema import validate, ValidationError


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigManager:
    """Manages configuration loading, validation, and access."""

    def __init__(self, config_path: str):
        """
        Initialize ConfigManager with path to config file.

        Args:
            config_path: Path to the JSON configuration file
        """
        self.config_path = Path(config_path)
        self.schema_path = Path(__file__).parent / "config_schema.json"
        self._config = None
        self._schema = None

        self._load_schema()
        self._load_config()
        self._validate_config()

    def _load_schema(self) -> None:
        """Load the configuration schema."""
        try:
            with open(self.schema_path, 'r') as f:
                self._schema = json.load(f)
        except FileNotFoundError:
            raise ConfigValidationError(f"Schema file not found: {self.schema_path}")
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in schema file: {e}")

    def _load_config(self) -> None:
        """Load the configuration file."""
        if not self.config_path.exists():
            raise ConfigValidationError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)

        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Error reading config file: {e}")

    def _validate_config(self) -> None:
        """Validate the configuration against the schema."""
        try:
            validate(instance=self._config, schema=self._schema)
        except ValidationError as e:
            raise ConfigValidationError(f"Configuration validation error: {e.message}")

    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the config value (e.g., 'output.mode')
            default: Default value if key is not found

        Returns:
            The configuration value or default
        """
        keys = key_path.split('.')
        value = self._config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def get_output_mode(self) -> str:
        """Get the output mode."""
        return self.get('output.mode')

    def should_confirm_changes(self) -> bool:
        """Check if changes should be confirmed."""
        return self.get('output.confirm_changes', True)

    def should_show_diffs(self) -> bool:
        """Check if diffs should be shown."""
        return self.get('output.show_diffs', True)

    def get_new_files_suffix(self) -> str:
        """Get the suffix for new files."""
        return self.get('output.new_files_suffix', '_formatted')

    def get_include_patterns(self) -> list:
        """Get file include patterns."""
        return self.get('file_selection.include_patterns', ['*.py'])

    def get_exclude_patterns(self) -> list:
        """Get file exclude patterns."""
        return self.get('file_selection.exclude_patterns', [])

    def is_recursive(self) -> bool:
        """Check if search should be recursive."""
        return self.get('file_selection.recursive', True)

    def get_naming_convention(self, element_type: str) -> Optional[str]:
        """
        Get naming convention for a specific element type.

        Args:
            element_type: Type of element (variables, functions, classes, etc.)

        Returns:
            Naming convention string or None if not specified
        """
        return self.get(f'naming_conventions.{element_type}')

    def is_rule_enabled(self, rule_name: str) -> bool:
        """
        Check if a specific rule is enabled.

        Args:
            rule_name: Name of the rule to check

        Returns:
            True if rule is enabled, False otherwise
        """
        return self.get(f'enabled_rules.{rule_name}', False)

    def get_formatting_rule(self, rule_name: str) -> Any:
        """
        Get a formatting rule value.

        Args:
            rule_name: Name of the formatting rule

        Returns:
            The rule value or None if not found
        """
        return self.get(f'formatting_rules.{rule_name}')

    def get_blank_lines_after_class(self) -> int:
        """Get the number of blank lines after class definitions."""
        return self.get('formatting_rules.blank_lines_after_class', 2)

    def get_blank_lines_after_function(self) -> int:
        """Get the number of blank lines after function definitions."""
        return self.get('formatting_rules.blank_lines_after_function', 1)

    def reload(self) -> None:
        """Reload the configuration from file."""
        self._load_config()
        self._validate_config()