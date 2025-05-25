"""
Cross-File Output Manager for Python Style Converter.
Handles coordinated transformations across multiple files with smart GUI behavior.
"""

import os
import shutil
import difflib
from typing import List, Optional, Tuple, Dict
from pathlib import Path
from dataclasses import dataclass

from config.config_manager import ConfigManager
from .rule_engine import ProcessingResult

# Import GUI diff viewer
try:
    from gui.diff_viewer import show_diff_gui
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


@dataclass
class CrossFileResult:
    """Result of cross-file transformation operation."""
    file_path: Path
    success: bool
    output_path: Optional[Path]
    error_message: Optional[str]
    is_definition_file: bool
    user_skipped: bool = False
    auto_applied: bool = False


@dataclass
class DefinitionFileGroup:
    """Group of files that are linked by definition-usage relationships."""
    definition_file: ProcessingResult
    usage_files: List[ProcessingResult]
    changed_symbols: List[str]


class CrossFileOutputManager:
    """Manages cross-file transformations with smart GUI behavior."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize with configuration."""
        self.config = config_manager
        self.output_mode = config_manager.get_output_mode()
        self.confirm_changes = config_manager.should_confirm_changes()
        self.show_diffs = config_manager.should_show_diffs()
        self.new_files_suffix = config_manager.get_new_files_suffix()

        # State tracking
        self.apply_to_all_definitions = False
        self.skip_all_definitions = False
        self.quit_requested = False

    def process_cross_file_results(self, results: List[ProcessingResult]) -> List[CrossFileResult]:
        """
        Process cross-file transformation results with smart GUI behavior.

        Workflow:
        1. Group files by definition-usage relationships
        2. Show GUI for definition files
        3. Auto-apply usage files when definition is confirmed

        Args:
            results: List of ProcessingResult objects from rule engine

        Returns:
            List of CrossFileResult objects
        """
        print("🌐 Processing cross-file transformations...")

        output_results = []

        # Handle failed results
        failed_results = [r for r in results if not r.success]
        for failed_result in failed_results:
            output_results.append(CrossFileResult(
                file_path=failed_result.file_path,
                success=False,
                output_path=None,
                error_message=f"Processing failed: {failed_result.error_message}",
                is_definition_file=False
            ))

        # Get successful results with changes
        successful_results = [r for r in results if r.success and self._has_actual_changes(r)]

        if not successful_results:
            print("ℹ️  No files need changes")
            return output_results

        # Group files by definition-usage relationships
        definition_groups = self._group_definition_and_usage_files(successful_results)

        print(f"📋 Found {len(definition_groups)} definition file groups")
        for group in definition_groups:
            print(f"   📝 {group.definition_file.file_path.name} → {len(group.usage_files)} usage files")

        # Process each definition group
        for group in definition_groups:
            if self.quit_requested:
                break

            # Process the definition file with GUI
            definition_result = self._process_definition_file(group)
            output_results.append(definition_result)

            if definition_result.error_message == "USER_QUIT":
                break

            # If definition was applied, auto-apply usage files
            if definition_result.success and not definition_result.user_skipped:
                for usage_file in group.usage_files:
                    usage_result = self._auto_apply_usage_file(usage_file)
                    output_results.append(usage_result)

        return output_results

    def _has_actual_changes(self, result: ProcessingResult) -> bool:
        """Check if result has actual changes to apply."""
        return (result.transformed_code and
                result.transformed_code != result.original_code and
                len(result.changes_made) > 0)

    def _group_definition_and_usage_files(self, results: List[ProcessingResult]) -> List[DefinitionFileGroup]:
        """
        Group files into definition-usage relationships.

        Logic:
        - Definition files have changes WITHOUT "(cross-file)" marker
        - Usage files have changes WITH "(cross-file)" marker
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
        # Use file paths as identifiers instead of objects
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
        import re

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

    def _process_definition_file(self, group: DefinitionFileGroup) -> CrossFileResult:
        """
        Process a definition file with GUI, showing usage impact.
        """
        result = group.definition_file

        try:
            # Handle "apply to all" or "skip all" from previous choices
            if self.apply_to_all_definitions:
                should_apply = True
                print(f"✅ Auto-applying to {result.file_path.name} (apply to all definitions)")
            elif self.skip_all_definitions:
                print(f"⏩ Auto-skipping {result.file_path.name} (skip all definitions)")
                return CrossFileResult(
                    file_path=result.file_path,
                    success=True,
                    output_path=result.file_path,
                    error_message=None,
                    is_definition_file=True,
                    user_skipped=True
                )
            else:
                # Show GUI with usage impact information
                should_apply = self._show_definition_gui(result, group)

                if should_apply is None:  # User quit
                    self.quit_requested = True
                    return CrossFileResult(
                        file_path=result.file_path,
                        success=False,
                        output_path=None,
                        error_message="USER_QUIT",
                        is_definition_file=True,
                        user_skipped=True
                    )

            if not should_apply:
                print(f"⏩ User skipped {result.file_path.name}")
                return CrossFileResult(
                    file_path=result.file_path,
                    success=True,
                    output_path=result.file_path,
                    error_message=None,
                    is_definition_file=True,
                    user_skipped=True
                )

            # Apply the changes
            print(f"✅ Applying definition changes to {result.file_path.name}")
            output_path = self._write_file_changes(result)

            return CrossFileResult(
                file_path=result.file_path,
                success=True,
                output_path=output_path,
                error_message=None,
                is_definition_file=True
            )

        except Exception as e:
            return CrossFileResult(
                file_path=result.file_path,
                success=False,
                output_path=None,
                error_message=str(e),
                is_definition_file=True
            )

    def _show_definition_gui(self, result: ProcessingResult, group: DefinitionFileGroup) -> Optional[bool]:
        """Show GUI for definition file with usage impact information."""

        # Create enhanced changes list with usage impact
        enhanced_changes = result.changes_made.copy()

        if group.usage_files:
            enhanced_changes.append("")  # Separator
            enhanced_changes.append(f"📋 This will automatically update {len(group.usage_files)} usage files:")

            for usage_file in group.usage_files[:5]:  # Show max 5 files
                enhanced_changes.append(f"   • {usage_file.file_path.name}")

            if len(group.usage_files) > 5:
                enhanced_changes.append(f"   • ... and {len(group.usage_files) - 5} more files")

        print(f"🎨 Showing GUI for definition file: {result.file_path.name}")

        if self.show_diffs and GUI_AVAILABLE:
            try:
                apply_changes, apply_to_all = show_diff_gui(
                    result.file_path,
                    result.original_code,
                    result.transformed_code,
                    enhanced_changes
                )

                # Handle "apply to all" choice
                if apply_to_all:
                    if apply_changes:
                        self.apply_to_all_definitions = True
                        print("✅ Will apply to all remaining definition files")
                    else:
                        self.skip_all_definitions = True
                        print("⏩ Will skip all remaining definition files")

                return apply_changes

            except Exception as e:
                print(f"❌ GUI error: {e}")
                return self._console_confirmation(result, enhanced_changes)
        else:
            return self._console_confirmation(result, enhanced_changes)

    def _console_confirmation(self, result: ProcessingResult, changes: List[str]) -> Optional[bool]:
        """Console fallback for confirmation."""
        print(f"\n📄 Apply changes to {result.file_path}?")
        for change in changes:
            print(f"  {change}")

        while True:
            response = input("\nApply changes? [y/n/q] (yes/no/quit): ").lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            elif response in ['q', 'quit']:
                return None
            else:
                print("Please enter 'y', 'n', or 'q'")

    def _auto_apply_usage_file(self, result: ProcessingResult) -> CrossFileResult:
        """Automatically apply changes to a usage file."""
        try:
            print(f"🔄 Auto-updating usage file: {result.file_path.name}")

            output_path = self._write_file_changes(result)

            return CrossFileResult(
                file_path=result.file_path,
                success=True,
                output_path=output_path,
                error_message=None,
                is_definition_file=False,
                auto_applied=True
            )

        except Exception as e:
            return CrossFileResult(
                file_path=result.file_path,
                success=False,
                output_path=None,
                error_message=str(e),
                is_definition_file=False
            )

    def _write_file_changes(self, result: ProcessingResult) -> Path:
        """Write transformed code to file."""
        if self.output_mode == "in_place":
            return self._write_in_place(result)
        elif self.output_mode == "new_files":
            return self._write_new_file(result)
        else:
            raise ValueError(f"Unknown output mode: {self.output_mode}")

    def _write_in_place(self, result: ProcessingResult) -> Path:
        """Write changes back to original file."""
        backup_path = result.file_path.with_suffix(result.file_path.suffix + '.backup')
        shutil.copy2(result.file_path, backup_path)

        try:
            with open(result.file_path, 'w', encoding='utf-8') as f:
                f.write(result.transformed_code)
            backup_path.unlink()
            return result.file_path
        except Exception as e:
            if backup_path.exists():
                shutil.copy2(backup_path, result.file_path)
                backup_path.unlink()
            raise e

    def _write_new_file(self, result: ProcessingResult) -> Path:
        """Write changes to new file."""
        original_path = result.file_path
        stem = original_path.stem
        suffix = original_path.suffix

        new_filename = f"{stem}{self.new_files_suffix}{suffix}"
        new_path = original_path.parent / new_filename

        counter = 1
        while new_path.exists():
            new_filename = f"{stem}{self.new_files_suffix}_{counter}{suffix}"
            new_path = original_path.parent / new_filename
            counter += 1

        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(result.transformed_code)

        return new_path

    def print_cross_file_summary(self, results: List[CrossFileResult]) -> None:
        """Print summary of cross-file transformations."""
        total_files = len(results)
        definition_files = len([r for r in results if r.is_definition_file])
        usage_files = len([r for r in results if not r.is_definition_file])
        successful = len([r for r in results if r.success and not r.user_skipped])
        auto_applied = len([r for r in results if r.auto_applied])
        failed = len([r for r in results if not r.success and r.error_message != "USER_QUIT"])
        skipped = len([r for r in results if r.user_skipped])

        print(f"\n{'='*60}")
        print("CROSS-FILE TRANSFORMATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total files processed: {total_files}")
        print(f"  • Definition files: {definition_files}")
        print(f"  • Usage files: {usage_files}")
        print(f"Successfully transformed: {successful}")
        print(f"  • Auto-applied usage files: {auto_applied}")
        if failed > 0:
            print(f"Failed: {failed}")
        if skipped > 0:
            print(f"Skipped by user: {skipped}")

        if successful > 0:
            print(f"\n✅ Successfully transformed files:")
            for result in results:
                if result.success and not result.user_skipped:
                    status = " (auto-applied)" if result.auto_applied else ""
                    file_type = "📝" if result.is_definition_file else "🔗"
                    print(f"  {file_type} {result.file_path}{status}")

        print(f"{'='*60}")


# For backwards compatibility, create an alias
OutputManager = CrossFileOutputManager