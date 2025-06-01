"""
Naming Convention Converter for Python Style Converter.
Handles all naming convention transformations (snake_case, camelCase, PascalCase, etc.).
"""

import re
from typing import Optional

from config.config_manager import ConfigManager
from core.code_element_extractor import CodeElement


class NamingConverter:
    """Handles naming convention conversions for code elements."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the naming converter.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config = config_manager

    def get_transformed_name(self, element: CodeElement) -> Optional[str]:
        """
        Get the transformed name for a code element based on configuration.

        Args:
            element: CodeElement to transform

        Returns:
            New name if transformation should be applied, None otherwise
        """
        # Map element types to configuration keys
        element_type_mapping = {
            'variable': 'variables',
            'function': 'functions',
            'class': 'classes',
            'constant': 'constants',
            'method': 'functions',  # Regular methods use function naming
            'private_method': 'private_methods',
            'dunder_method': 'dunder_methods'
        }

        # Map element types to rule names
        rule_mapping = {
            'variable': 'variable_naming',
            'function': 'function_naming',
            'class': 'class_naming',
            'constant': 'constant_naming',
            'method': 'function_naming',
            'private_method': 'private_method_naming',
            'dunder_method': 'dunder_method_naming'
        }

        config_key = element_type_mapping.get(element.element_type)
        rule_name = rule_mapping.get(element.element_type)

        if not config_key or not rule_name:
            return None

        if not self.config.is_rule_enabled(rule_name):
            return None

        target_convention = self.config.get_naming_convention(config_key)
        if not target_convention:
            return None

        return self.convert_naming_convention(element.name, target_convention)

    def convert_naming_convention(self, name: str, target_convention: str) -> str:
        """
        Convert a name to the specified naming convention.

        Args:
            name: Original name
            target_convention: Target naming convention

        Returns:
            Converted name
        """
        if target_convention == "snake_case":
            return self._to_snake_case(name)
        elif target_convention == "camelCase":
            return self._to_camel_case(name)
        elif target_convention == "PascalCase":
            return self._to_pascal_case(name)
        elif target_convention == "UPPER_CASE":
            return self._to_upper_case(name)
        elif target_convention == "_snake_case":
            base_name = self._to_snake_case(name.lstrip('_'))
            return f"_{base_name}"
        elif target_convention == "_camelCase":
            base_name = self._to_camel_case(name.lstrip('_'))
            return f"_{base_name}"
        elif target_convention == "__snake_case__":
            base_name = self._to_snake_case(name.strip('_'))
            return f"__{base_name}__"
        elif target_convention == "__camelCase__":
            base_name = self._to_camel_case(name.strip('_'))
            return f"__{base_name}__"
        else:
            return name

    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        # Handle already snake_case names
        if '_' in name and name.islower():
            return name

        # Convert camelCase and PascalCase to snake_case
        # Insert underscore before uppercase letters that follow lowercase letters
        result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)

        # Handle sequences of uppercase letters
        result = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', result)

        return result.lower()

    def _to_camel_case(self, name: str) -> str:
        """Convert name to camelCase."""
        if '_' in name:
            # Convert from snake_case
            parts = name.lower().split('_')
            return parts[0] + ''.join(word.capitalize() for word in parts[1:])
        else:
            # Assume it's already in some form of camelCase/PascalCase
            return name[0].lower() + name[1:] if name else name

    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase."""
        if '_' in name:
            # Convert from snake_case
            parts = name.lower().split('_')
            return ''.join(word.capitalize() for word in parts)
        else:
            # Assume it's already in some form of camelCase/PascalCase
            return name[0].upper() + name[1:] if name else name

    def _to_upper_case(self, name: str) -> str:
        """Convert name to UPPER_CASE."""
        if '_' in name:
            return name.upper()
        else:
            # Convert camelCase/PascalCase to UPPER_CASE
            snake_case = self._to_snake_case(name)
            return snake_case.upper()

    def is_naming_rules_enabled(self) -> bool:
        """Check if any naming rules are enabled."""
        naming_rules = [
            'variable_naming',
            'function_naming',
            'class_naming',
            'constant_naming',
            'private_method_naming',
            'dunder_method_naming'
        ]
        return any(self.config.is_rule_enabled(rule) for rule in naming_rules)