"""
Cross-File Output Manager for Python Style Converter.
Orchestrates cross-file transformations with smart GUI behavior.
Simplified and focused on coordination rather than implementation details.
"""

from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

from config.config_manager import ConfigManager
from .rule_engine import ProcessingResult
from .cross_file_processor import CrossFileProcessor, DefinitionFileGroup
from .file_writer import FileWriter

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


class CrossFileOutputManager:
    """Manages cross-file transformations with smart GUI behavior."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize with configuration."""
        self.config = config_manager
        self.confirm_changes = config_manager.should_confirm_changes()
        self.show_diffs = config_manager.should_show_diffs()

        # Initialize components
        self.processor = CrossFileProcessor()
        self.file_writer = FileWriter(config_manager)

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
        successful_results = [r for r in results if r.success and self.processor.has_actual_changes(r)]

        if not successful_results:
            print("ℹ️  No files need changes")
            return output_results

        # Group files by definition-usage relationships
        definition_groups = self.processor.group_definition_and_usage_files(successful_results)

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

    def _process_definition_file(self, group: DefinitionFileGroup) -> CrossFileResult:
        """Process a definition file with GUI, showing usage impact."""
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
            write_result = self.file_writer.write_transformed_code(result.file_path, result.transformed_code)

            return CrossFileResult(
                file_path=result.file_path,
                success=write_result.success,
                output_path=write_result.output_path,
                error_message=write_result.error_message,
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
        enhanced_changes = self.processor.create_enhanced_changes_list(result, group)

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

            write_result = self.file_writer.write_transformed_code(result.file_path, result.transformed_code)

            return CrossFileResult(
                file_path=result.file_path,
                success=write_result.success,
                output_path=write_result.output_path,
                error_message=write_result.error_message,
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