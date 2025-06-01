"""
Cross-File Processor for Python Style Converter.
Handles grouping files by definition-usage relationships and processing logic.
"""

import re
from typing import List, Dict
from pathlib import Path
from dataclasses import dataclass

from .rule_engine import ProcessingResult


@dataclass
class DefinitionFileGroup:
    """Group of files that are linked by definition-usage relationships."""
    definition_file: ProcessingResult
    usage_files: List[ProcessingResult]
    changed_symbols: List[str]


class CrossFileProcessor:
    """Processes cross-file relationships and groups files by dependencies."""

    def __init__(self):
        """Initialize the cross-file processor."""
        pass

    def group_definition_and_usage_files(self, results: List[ProcessingResult]) -> List[DefinitionFileGroup]:
        """
        Group files into definition-usage relationships.

        Logic:
        - Definition files have changes WITHOUT "(cross-file)" marker
        - Usage files have changes WITH "(cross-file)" marker

        Args:
            results: List of ProcessingResult objects

        Returns:
            List of DefinitionFileGroup objects
        """
        definition_files = []
        usage_files = []

        # Separate definition and usage files
        for result in results:
            if self._is_definition_file(result):
                definition_files.append(result)
            else:
                usage_files.append(result)

        print(f"🔍 Categorization: {len(definition_files)} definition files, {len(usage_files)} usage files")

        # Group definition files with their related usage files
        groups = []
        for def_file in definition_files:
            # Extract symbols being changed in this definition file
            changed_symbols = self._extract_changed_symbols(def_file)

            # Find usage files that reference these symbols
            related_usage_files = []
            for usage_file in usage_files:
                if self._usage_file_references_symbols(usage_file, changed_symbols):
                    related_usage_files.append(usage_file)

            groups.append(DefinitionFileGroup(
                definition_file=def_file,
                usage_files=related_usage_files,
                changed_symbols=changed_symbols
            ))

        # Handle orphaned usage files (usage files not linked to any definition)
        linked_usage_file_paths = set()
        for group in groups:
            for usage_file in group.usage_files:
                linked_usage_file_paths.add(usage_file.file_path)

        orphaned_usage_files = [f for f in usage_files if f.file_path not in linked_usage_file_paths]
        for orphan in orphaned_usage_files:
            # Create a group with just the usage file
            groups.append(DefinitionFileGroup(
                definition_file=orphan,  # Treat as definition for GUI purposes
                usage_files=[],
                changed_symbols=self._extract_changed_symbols(orphan)
            ))

        return groups

    def has_actual_changes(self, result: ProcessingResult) -> bool:
        """Check if result has actual changes to apply."""
        return (result.transformed_code and
                result.transformed_code != result.original_code and
                len(result.changes_made) > 0)

    def _is_definition_file(self, result: ProcessingResult) -> bool:
        """
        Check if a file contains symbol definitions (not just usages).

        Logic: Definition files have changes WITHOUT "(cross-file)" marker
        """
        for change in result.changes_made:
            if "(cross-file)" not in change:
                return True
        return False

    def _extract_changed_symbols(self, result: ProcessingResult) -> List[str]:
        """Extract the names of symbols being changed."""
        symbols = []

        for change in result.changes_made:
            # Look for pattern: "Renamed X 'old_name' to 'new_name'"
            match = re.search(r"'([^']+)' to '([^']+)'", change)
            if match:
                old_name = match.group(1)
                symbols.append(old_name)

        return symbols

    def _usage_file_references_symbols(self, usage_file: ProcessingResult, symbols: List[str]) -> bool:
        """Check if a usage file references any of the given symbols."""
        for change in usage_file.changes_made:
            for symbol in symbols:
                if symbol in change:
                    return True
        return False

    def create_enhanced_changes_list(self, result: ProcessingResult, group: DefinitionFileGroup) -> List[str]:
        """Create enhanced changes list with usage impact information for GUI display."""
        enhanced_changes = result.changes_made.copy()

        if group.usage_files:
            enhanced_changes.append("")  # Separator
            enhanced_changes.append(f"📋 This will automatically update {len(group.usage_files)} usage files:")

            for usage_file in group.usage_files[:5]:  # Show max 5 files
                enhanced_changes.append(f"   • {usage_file.file_path.name}")

            if len(group.usage_files) > 5:
                enhanced_changes.append(f"   • ... and {len(group.usage_files) - 5} more files")

        return enhanced_changes