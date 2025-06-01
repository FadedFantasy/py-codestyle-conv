"""
Global Transformation Generator for Python Style Converter.
Generates cross-file transformations by analyzing symbol definitions across the project.
"""

from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass

from config.config_manager import ConfigManager
from .global_symbol_tracker import GlobalSymbolMap, SymbolDefinition
from .naming_converter import NamingConverter


@dataclass
class GlobalTransformation:
    """Represents a transformation that affects multiple files."""
    old_name: str
    new_name: str
    symbol_type: str  # 'class', 'function', 'variable', 'constant'
    definition_file: Path
    affected_files: List[Path]
    transformation_type: str  # 'naming_convention', 'formatting', etc.


class GlobalTransformationGenerator:
    """Generates cross-file transformations based on symbol analysis."""

    def __init__(self, config_manager: ConfigManager, global_symbol_map: GlobalSymbolMap):
        """
        Initialize the global transformation generator.

        Args:
            config_manager: ConfigManager instance with loaded configuration
            global_symbol_map: Global symbol map with cross-file relationships
        """
        self.config = config_manager
        self.global_symbol_map = global_symbol_map
        self.naming_converter = NamingConverter(config_manager)

    def generate_global_transformations(self) -> List[GlobalTransformation]:
        """
        Generate global transformations by analyzing all symbol definitions
        and determining which ones need to be renamed according to configuration.

        Returns:
            List of GlobalTransformation objects
        """
        transformations = []

        print("🔍 Analyzing symbols for global transformations...")

        # Process each unique symbol defined in the project
        for symbol_name, definitions in self.global_symbol_map.definitions.items():
            if not definitions:
                continue

            # Get the primary definition (first one, or one in main module)
            primary_def = self._get_primary_definition(definitions)
            if not primary_def:
                continue

            # Check if this symbol should be transformed
            new_name = self.naming_converter.get_transformed_name(primary_def.element)
            if new_name and new_name != symbol_name:
                # Find all files affected by this transformation
                affected_files = self._get_affected_files(symbol_name)

                transformation = GlobalTransformation(
                    old_name=symbol_name,
                    new_name=new_name,
                    symbol_type=primary_def.symbol_type,
                    definition_file=primary_def.file_path,
                    affected_files=affected_files,
                    transformation_type='naming_convention'
                )
                transformations.append(transformation)

                print(f"🎯 Global transformation: {symbol_name} → {new_name} (affects {len(affected_files)} files)")

        print(f"✅ Generated {len(transformations)} global transformations")
        return transformations

    def _get_primary_definition(self, definitions: List[SymbolDefinition]) -> Optional[SymbolDefinition]:
        """
        Get the primary definition for a symbol when there are multiple definitions.

        Args:
            definitions: List of symbol definitions

        Returns:
            Primary definition to use for transformation decisions
        """
        if len(definitions) == 1:
            return definitions[0]

        # If multiple definitions, prefer:
        # 1. Non-test files over test files
        # 2. Files closer to project root
        # 3. First definition found

        non_test_defs = [d for d in definitions if 'test' not in str(d.file_path).lower()]
        if non_test_defs:
            return sorted(non_test_defs, key=lambda d: len(d.file_path.parts))[0]

        return definitions[0]

    def _get_affected_files(self, symbol_name: str) -> List[Path]:
        """
        Get all files that are affected by renaming a symbol.

        Args:
            symbol_name: Name of the symbol being renamed

        Returns:
            List of file paths that contain references to this symbol
        """
        affected_files = set()

        # Add files where symbol is defined
        for definition in self.global_symbol_map.definitions.get(symbol_name, []):
            affected_files.add(definition.file_path)

        # Add files where symbol is used
        for usage in self.global_symbol_map.usages.get(symbol_name, []):
            affected_files.add(usage.file_path)

        # Add files that import this symbol
        for import_stmt in self.global_symbol_map.imports:
            if symbol_name in import_stmt.imported_names:
                affected_files.add(import_stmt.file_path)

        return list(affected_files)

    def get_transformations_for_file(self, file_path: Path, global_transformations: List[GlobalTransformation]) -> Dict[str, str]:
        """
        Get cross-file transformations that affect a specific file.

        Args:
            file_path: Path to the file
            global_transformations: List of global transformations

        Returns:
            Dictionary mapping old names to new names for this file
        """
        transformations = {}

        for global_transform in global_transformations:
            if file_path in global_transform.affected_files:
                transformations[global_transform.old_name] = global_transform.new_name

        return transformations

    def get_symbol_type_for_file(self, symbol_name: str, file_path: Path) -> str:
        """Get the symbol type for a symbol in a specific file."""
        # Check definitions in this file
        for definition in self.global_symbol_map.definitions.get(symbol_name, []):
            if definition.file_path == file_path:
                return definition.symbol_type

        # Check usages to infer type
        for usage in self.global_symbol_map.usages.get(symbol_name, []):
            if usage.file_path == file_path:
                if 'class' in usage.context.lower():
                    return 'class'
                elif 'function' in usage.context.lower():
                    return 'function'

        return 'symbol'  # Generic fallback