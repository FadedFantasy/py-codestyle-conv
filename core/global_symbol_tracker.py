"""
Global Symbol Tracker for Python Style Converter.
Simplified orchestrator for analyzing cross-file symbol definitions and usages.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict

from .symbol_definitions import GlobalSymbolMap, SymbolDefinition, SymbolUsage
from .module_mapper import ModuleMapper
from .symbol_analyzer import SymbolAnalyzer


class GlobalSymbolTracker:
    """Simplified tracker for cross-file symbol relationships."""

    def __init__(self, project_root: Path):
        """
        Initialize the global symbol tracker.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.symbol_map = GlobalSymbolMap()
        self.module_mapper = ModuleMapper(project_root)
        self.symbol_analyzer = SymbolAnalyzer()

    def analyze_project(self, file_paths: List[Path]) -> GlobalSymbolMap:
        """
        Analyze all files in the project to build a global symbol map.

        Args:
            file_paths: List of Python files to analyze

        Returns:
            GlobalSymbolMap containing cross-file symbol information
        """
        print(f"🔍 Analyzing {len(file_paths)} files for cross-file symbols...")

        # First pass: Build file-to-module mapping
        self.symbol_map.file_to_module, self.symbol_map.module_to_file = (
            self.module_mapper.build_module_mapping(file_paths)
        )

        # Second pass: Extract definitions and imports
        for file_path in file_paths:
            try:
                self._analyze_file_definitions(file_path)
                self._analyze_file_imports(file_path)
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze {file_path}: {e}")
                continue

        # Third pass: Find symbol usages
        for file_path in file_paths:
            try:
                self._analyze_file_usages(file_path)
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze usages in {file_path}: {e}")
                continue

        self._print_analysis_summary()
        return self.symbol_map

    def _analyze_file_definitions(self, file_path: Path) -> None:
        """Analyze a single file for symbol definitions."""
        definitions = self.symbol_analyzer.analyze_file_definitions(file_path)

        for definition in definitions:
            self.symbol_map.definitions[definition.name].append(definition)

    def _analyze_file_imports(self, file_path: Path) -> None:
        """Analyze import statements in a file."""
        imports = self.symbol_analyzer.analyze_file_imports(file_path)
        self.symbol_map.imports.extend(imports)

    def _analyze_file_usages(self, file_path: Path) -> None:
        """Analyze symbol usages in a file."""
        # Get imported symbols for this file
        imported_symbols = self.symbol_analyzer.get_imported_symbols_for_file(
            file_path, self.symbol_map.imports
        )

        # Analyze usages
        usages = self.symbol_analyzer.analyze_file_usages(file_path, imported_symbols)

        for usage in usages:
            self.symbol_map.usages[usage.name].append(usage)

    def _print_analysis_summary(self) -> None:
        """Print a summary of the symbol analysis."""
        total_definitions = sum(len(defs) for defs in self.symbol_map.definitions.values())
        total_usages = sum(len(usages) for usages in self.symbol_map.usages.values())

        print(f"📊 Symbol Analysis Summary:")
        print(f"   • Found {total_definitions} symbol definitions")
        print(f"   • Found {total_usages} symbol usages")
        print(f"   • Found {len(self.symbol_map.imports)} import statements")
        print(f"   • Analyzed {len(self.symbol_map.file_to_module)} files")

    def get_cross_file_references(self, symbol_name: str) -> Tuple[List[SymbolDefinition], List[SymbolUsage]]:
        """
        Get all cross-file references for a symbol.

        Args:
            symbol_name: Name of the symbol to analyze

        Returns:
            Tuple of (definitions, usages) across all files
        """
        definitions = self.symbol_map.definitions.get(symbol_name, [])
        usages = self.symbol_map.usages.get(symbol_name, [])

        return definitions, usages

    def get_symbols_to_rename(self, old_name: str, new_name: str) -> Dict[Path, List[Tuple[int, str, str]]]:
        """
        Get all locations where a symbol needs to be renamed.

        Args:
            old_name: Current symbol name
            new_name: New symbol name

        Returns:
            Dictionary mapping file paths to list of (line_number, old_text, new_text) tuples
        """
        rename_locations = defaultdict(list)

        # Add definitions
        for definition in self.symbol_map.definitions.get(old_name, []):
            rename_locations[definition.file_path].append((
                definition.line_number,
                old_name,
                new_name
            ))

        # Add usages
        for usage in self.symbol_map.usages.get(old_name, []):
            rename_locations[usage.file_path].append((
                usage.line_number,
                old_name,
                new_name
            ))

        return dict(rename_locations)