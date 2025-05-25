"""
Naming convention utilities for Python Style Converter.
Provides functions to convert between different naming conventions.
"""

import re
from typing import List, Tuple


class NamingConverter:
    """Utility class for converting between naming conventions."""

    @staticmethod
    def to_snake_case(name: str) -> str:
        """
        Convert name to snake_case.

        Args:
            name: Name to convert

        Returns:
            Name in snake_case format

        Examples:
            >>> NamingConverter.to_snake_case("camelCase")
            'camel_case'
            >>> NamingConverter.to_snake_case("PascalCase")
            'pascal_case'
            >>> NamingConverter.to_snake_case("already_snake")
            'already_snake'
        """
        # Handle already snake_case names
        if '_' in name and name.islower():
            return name

        # Convert camelCase and PascalCase to snake_case
        # Insert underscore before uppercase letters that follow lowercase letters or digits
        result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)

        # Handle sequences of uppercase letters (e.g., "HTTPSConnection" -> "HTTPS_Connection")
        result = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', result)

        return result.lower()

    @staticmethod
    def to_camel_case(name: str) -> str:
        """
        Convert name to camelCase.

        Args:
            name: Name to convert

        Returns:
            Name in camelCase format

        Examples:
            >>> NamingConverter.to_camel_case("snake_case")
            'snakeCase'
            >>> NamingConverter.to_camel_case("PascalCase")
            'pascalCase'
            >>> NamingConverter.to_camel_case("alreadyCamel")
            'alreadyCamel'
        """
        if '_' in name:
            # Convert from snake_case
            parts = name.lower().split('_')
            if not parts:
                return name
            return parts[0] + ''.join(word.capitalize() for word in parts[1:])
        else:
            # Assume it's already in some form of camelCase/PascalCase
            return name[0].lower() + name[1:] if name else name

    @staticmethod
    def to_pascal_case(name: str) -> str:
        """
        Convert name to PascalCase.

        Args:
            name: Name to convert

        Returns:
            Name in PascalCase format

        Examples:
            >>> NamingConverter.to_pascal_case("snake_case")
            'SnakeCase'
            >>> NamingConverter.to_pascal_case("camelCase")
            'CamelCase'
            >>> NamingConverter.to_pascal_case("AlreadyPascal")
            'AlreadyPascal'
        """
        if '_' in name:
            # Convert from snake_case
            parts = name.lower().split('_')
            return ''.join(word.capitalize() for word in parts if word)
        else:
            # Assume it's already in some form of camelCase/PascalCase
            return name[0].upper() + name[1:] if name else name

    @staticmethod
    def to_upper_case(name: str) -> str:
        """
        Convert name to UPPER_CASE (screaming snake case).

        Args:
            name: Name to convert

        Returns:
            Name in UPPER_CASE format

        Examples:
            >>> NamingConverter.to_upper_case("snake_case")
            'SNAKE_CASE'
            >>> NamingConverter.to_upper_case("camelCase")
            'CAMEL_CASE'
            >>> NamingConverter.to_upper_case("PascalCase")
            'PASCAL_CASE'
        """
        if '_' in name:
            return name.upper()
        else:
            # Convert camelCase/PascalCase to UPPER_CASE
            snake_case = NamingConverter.to_snake_case(name)
            return snake_case.upper()

    @staticmethod
    def detect_naming_convention(name: str) -> str:
        """
        Detect the naming convention of a given name.

        Args:
            name: Name to analyze

        Returns:
            Detected naming convention: 'snake_case', 'camelCase', 'PascalCase',
            'UPPER_CASE', or 'mixed'

        Examples:
            >>> NamingConverter.detect_naming_convention("snake_case")
            'snake_case'
            >>> NamingConverter.detect_naming_convention("camelCase")
            'camelCase'
            >>> NamingConverter.detect_naming_convention("PascalCase")
            'PascalCase'
            >>> NamingConverter.detect_naming_convention("UPPER_CASE")
            'UPPER_CASE'
        """
        if not name:
            return 'unknown'

        # Check for UPPER_CASE (all uppercase with underscores)
        if name.isupper() and ('_' in name or name.isalpha()):
            return 'UPPER_CASE'

        # Check for snake_case (lowercase with underscores)
        if '_' in name and name.islower():
            return 'snake_case'

        # Check for PascalCase (starts with uppercase, no underscores)
        if not '_' in name and name[0].isupper() and any(c.islower() for c in name):
            return 'PascalCase'

        # Check for camelCase (starts with lowercase, no underscores, has uppercase)
        if not '_' in name and name[0].islower() and any(c.isupper() for c in name):
            return 'camelCase'

        # Check for single word lowercase
        if name.islower() and '_' not in name:
            return 'snake_case'

        # Check for single word uppercase
        if name.isupper() and '_' not in name:
            return 'UPPER_CASE'

        return 'mixed'

    @staticmethod
    def convert_to_convention(name: str, target_convention: str) -> str:
        """
        Convert name to the specified naming convention.

        Args:
            name: Name to convert
            target_convention: Target convention ('snake_case', 'camelCase',
                             'PascalCase', 'UPPER_CASE', '_snake_case',
                             '_camelCase', '__snake_case__', '__camelCase__')

        Returns:
            Converted name

        Raises:
            ValueError: If target_convention is not supported
        """
        if target_convention == "snake_case":
            return NamingConverter.to_snake_case(name)
        elif target_convention == "camelCase":
            return NamingConverter.to_camel_case(name)
        elif target_convention == "PascalCase":
            return NamingConverter.to_pascal_case(name)
        elif target_convention == "UPPER_CASE":
            return NamingConverter.to_upper_case(name)
        elif target_convention == "_snake_case":
            base_name = NamingConverter.to_snake_case(name.lstrip('_'))
            return f"_{base_name}"
        elif target_convention == "_camelCase":
            base_name = NamingConverter.to_camel_case(name.lstrip('_'))
            return f"_{base_name}"
        elif target_convention == "__snake_case__":
            base_name = NamingConverter.to_snake_case(name.strip('_'))
            return f"__{base_name}__"
        elif target_convention == "__camelCase__":
            base_name = NamingConverter.to_camel_case(name.strip('_'))
            return f"__{base_name}__"
        else:
            raise ValueError(f"Unsupported naming convention: {target_convention}")

    @staticmethod
    def is_valid_python_identifier(name: str) -> bool:
        """
        Check if a name is a valid Python identifier.

        Args:
            name: Name to check

        Returns:
            True if the name is a valid Python identifier, False otherwise
        """
        return name.isidentifier()

    @staticmethod
    def get_supported_conventions() -> List[str]:
        """
        Get list of all supported naming conventions.

        Returns:
            List of supported convention names
        """
        return [
            "snake_case",
            "camelCase",
            "PascalCase",
            "UPPER_CASE",
            "_snake_case",
            "_camelCase",
            "__snake_case__",
            "__camelCase__"
        ]

    @staticmethod
    def split_compound_name(name: str) -> List[str]:
        """
        Split a compound name into its constituent words.

        Args:
            name: Name to split

        Returns:
            List of words that make up the name

        Examples:
            >>> NamingConverter.split_compound_name("camelCase")
            ['camel', 'Case']
            >>> NamingConverter.split_compound_name("snake_case")
            ['snake', 'case']
            >>> NamingConverter.split_compound_name("UPPER_CASE")
            ['UPPER', 'CASE']
        """
        if '_' in name:
            # Snake case variants
            return [part for part in name.split('_') if part]
        else:
            # Camel case variants
            # Split on uppercase letters
            parts = re.findall(r'[A-Z]*[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', name)
            return parts if parts else [name]