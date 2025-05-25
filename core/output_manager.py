"""
Output manager for Python Style Converter.
Handles file output, diffs, confirmations, and different output modes.
Now includes GUI diff viewer integration.
"""

import os
import shutil
import difflib
from typing import List, Optional, Tuple
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
class OutputResult:
    """Result of output operation for a single file."""
    file_path: Path
    success: bool
    output_path: Optional[Path]
    error_message: Optional[str]
    user_skipped: bool = False


class OutputManager:
    """Manages output operations for processed files."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize OutputManager with configuration.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config = config_manager
        self.output_mode = config_manager.get_output_mode()
        self.confirm_changes = config_manager.should_confirm_changes()
        self.show_diffs = config_manager.should_show_diffs()
        self.new_files_suffix = config_manager.get_new_files_suffix()

        # GUI state tracking
        self.apply_to_all_remaining = False
        self.skip_all_remaining = False
        self.quit_requested = False

    def process_results(self, results: List[ProcessingResult]) -> List[OutputResult]:
        """
        Process all transformation results and handle output.

        Args:
            results: List of ProcessingResult objects from rule engine

        Returns:
            List of OutputResult objects indicating success/failure of output operations
        """
        output_results = []

        # Filter out unsuccessful processing results
        successful_results = [r for r in results if r.success and r.transformed_code]
        failed_results = [r for r in results if not r.success]

        # Report failed processing
        for failed_result in failed_results:
            output_results.append(OutputResult(
                file_path=failed_result.file_path,
                success=False,
                output_path=None,
                error_message=f"Processing failed: {failed_result.error_message}"
            ))

        # Process successful transformations
        for result in successful_results:
            # Check if user requested to quit
            if self.quit_requested:
                break

            if self._has_changes(result):
                output_result = self._handle_single_file_output(result)
                output_results.append(output_result)

                # Handle quit request
                if output_result.error_message == "USER_QUIT":
                    break
            else:
                # No changes to apply
                output_results.append(OutputResult(
                    file_path=result.file_path,
                    success=True,
                    output_path=result.file_path,
                    error_message=None
                ))

        return output_results

    def _has_changes(self, result: ProcessingResult) -> bool:
        """
        Check if the processing result contains actual changes.

        Args:
            result: ProcessingResult to check

        Returns:
            True if there are changes, False otherwise
        """
        return (result.transformed_code and
                result.transformed_code != result.original_code and
                len(result.changes_made) > 0)

    def _handle_single_file_output(self, result: ProcessingResult) -> OutputResult:
        """
        Handle output for a single file processing result.

        Args:
            result: ProcessingResult to handle

        Returns:
            OutputResult indicating success/failure
        """
        try:
            # Handle "apply to all" or "skip all" from previous GUI choices
            if self.apply_to_all_remaining:
                should_apply = True
            elif self.skip_all_remaining:
                return OutputResult(
                    file_path=result.file_path,
                    success=True,
                    output_path=result.file_path,
                    error_message=None,
                    user_skipped=True
                )
            else:
                # Show diff and get user choice
                should_apply = self._get_user_confirmation(result)

                # Handle quit request
                if should_apply is None:  # User quit
                    self.quit_requested = True
                    return OutputResult(
                        file_path=result.file_path,
                        success=False,
                        output_path=None,
                        error_message="USER_QUIT",
                        user_skipped=True
                    )

                if not should_apply:
                    return OutputResult(
                        file_path=result.file_path,
                        success=True,
                        output_path=result.file_path,
                        error_message=None,
                        user_skipped=True
                    )

            # Apply the changes
            output_path = self._write_output(result)

            return OutputResult(
                file_path=result.file_path,
                success=True,
                output_path=output_path,
                error_message=None
            )

        except Exception as e:
            return OutputResult(
                file_path=result.file_path,
                success=False,
                output_path=None,
                error_message=str(e)
            )

    def _get_user_confirmation(self, result: ProcessingResult) -> Optional[bool]:
        """
        Get user confirmation for applying changes.
        Uses GUI if available and show_diffs is enabled, otherwise console.

        Args:
            result: ProcessingResult to confirm

        Returns:
            True to apply, False to skip, None if user quit
        """
        if self.show_diffs and GUI_AVAILABLE:
            return self._show_gui_diff(result)
        else:
            return self._show_console_diff(result)

    def _show_gui_diff(self, result: ProcessingResult) -> Optional[bool]:
        """
        Show GUI diff viewer and get user choice.

        Args:
            result: ProcessingResult containing original and transformed code

        Returns:
            True to apply, False to skip, None if user quit
        """
        try:
            apply_changes, apply_to_all = show_diff_gui(
                result.file_path,
                result.original_code,
                result.transformed_code,
                result.changes_made
            )

            # Handle "apply to all" choice
            if apply_to_all:
                if apply_changes:
                    self.apply_to_all_remaining = True
                    print(f"Applying changes to all remaining files...")
                else:
                    self.skip_all_remaining = True
                    print(f"Skipping all remaining files...")

            return apply_changes

        except Exception as e:
            print(f"GUI diff viewer error: {e}")
            print("Falling back to console diff viewer...")
            return self._show_console_diff(result)

    def _show_console_diff(self, result: ProcessingResult) -> Optional[bool]:
        """
        Show console diff and get user choice (fallback method).

        Args:
            result: ProcessingResult containing original and transformed code

        Returns:
            True to apply, False to skip, None if user quit
        """
        if self.show_diffs:
            self._show_diff_console(result)

        if self.confirm_changes:
            return self._ask_for_confirmation_console(result)

        return True  # Apply by default if no confirmation needed

    def _show_diff_console(self, result: ProcessingResult) -> None:
        """
        Show diff between original and transformed code in console.

        Args:
            result: ProcessingResult containing original and transformed code
        """
        print(f"\n{'='*60}")
        print(f"Changes for: {result.file_path}")
        print(f"{'='*60}")

        if result.changes_made:
            print("Changes to be made:")
            for change in result.changes_made:
                print(f"  - {change}")
            print()

        # Generate unified diff
        diff_lines = list(difflib.unified_diff(
            result.original_code.splitlines(keepends=True),
            result.transformed_code.splitlines(keepends=True),
            fromfile=f"{result.file_path} (original)",
            tofile=f"{result.file_path} (transformed)",
            lineterm=""
        ))

        if diff_lines:
            print("Diff:")
            for line in diff_lines:
                print(line.rstrip())
        else:
            print("No visible differences in diff format.")

        print(f"{'='*60}")

    def _ask_for_confirmation_console(self, result: ProcessingResult) -> Optional[bool]:
        """
        Ask user for confirmation before applying changes (console version).

        Args:
            result: ProcessingResult to confirm

        Returns:
            True if user confirms, False to skip, None if quit
        """
        print(f"\nApply changes to {result.file_path}?")
        print("Changes:")
        for change in result.changes_made:
            print(f"  - {change}")

        while True:
            response = input("Apply changes? [y/n/q] (yes/no/quit): ").lower().strip()

            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            elif response in ['q', 'quit']:
                print("Quitting...")
                return None
            else:
                print("Please enter 'y' for yes, 'n' for no, or 'q' to quit.")

    def _write_output(self, result: ProcessingResult) -> Path:
        """
        Write the transformed code to output file.

        Args:
            result: ProcessingResult containing transformed code

        Returns:
            Path to the output file
        """
        if self.output_mode == "in_place":
            return self._write_in_place(result)
        elif self.output_mode == "new_files":
            return self._write_new_file(result)
        else:
            raise ValueError(f"Unknown output mode: {self.output_mode}")

    def _write_in_place(self, result: ProcessingResult) -> Path:
        """
        Write transformed code back to the original file.

        Args:
            result: ProcessingResult containing transformed code

        Returns:
            Path to the modified file (same as input)
        """
        # Create backup first
        backup_path = result.file_path.with_suffix(result.file_path.suffix + '.backup')
        shutil.copy2(result.file_path, backup_path)

        try:
            with open(result.file_path, 'w', encoding='utf-8') as f:
                f.write(result.transformed_code)

            # Remove backup if write was successful
            backup_path.unlink()

            return result.file_path

        except Exception as e:
            # Restore from backup if write failed
            if backup_path.exists():
                shutil.copy2(backup_path, result.file_path)
                backup_path.unlink()
            raise e

    def _write_new_file(self, result: ProcessingResult) -> Path:
        """
        Write transformed code to a new file.

        Args:
            result: ProcessingResult containing transformed code

        Returns:
            Path to the new file
        """
        # Generate new filename
        original_path = result.file_path
        stem = original_path.stem
        suffix = original_path.suffix

        new_filename = f"{stem}{self.new_files_suffix}{suffix}"
        new_path = original_path.parent / new_filename

        # Ensure we don't overwrite existing files
        counter = 1
        while new_path.exists():
            new_filename = f"{stem}{self.new_files_suffix}_{counter}{suffix}"
            new_path = original_path.parent / new_filename
            counter += 1

        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(result.transformed_code)

        return new_path

    def print_summary(self, output_results: List[OutputResult]) -> None:
        """
        Print a summary of all output operations.

        Args:
            output_results: List of OutputResult objects to summarize
        """
        total_files = len(output_results)
        successful = len([r for r in output_results if r.success and not r.user_skipped])
        failed = len([r for r in output_results if not r.success and r.error_message != "USER_QUIT"])
        skipped = len([r for r in output_results if r.user_skipped and r.error_message != "USER_QUIT"])
        quit_early = len([r for r in output_results if r.error_message == "USER_QUIT"])

        print(f"\n{'='*50}")
        print("PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"Total files processed: {total_files}")
        print(f"Successfully processed: {successful}")
        print(f"Failed: {failed}")
        print(f"Skipped by user: {skipped}")

        if quit_early > 0:
            print(f"Quit early: Processing stopped by user")

        if failed > 0:
            print(f"\nFailed files:")
            for result in output_results:
                if not result.success and result.error_message != "USER_QUIT":
                    print(f"  - {result.file_path}: {result.error_message}")

        if skipped > 0:
            print(f"\nSkipped files:")
            for result in output_results:
                if result.user_skipped and result.error_message != "USER_QUIT":
                    print(f"  - {result.file_path}")

        if successful > 0:
            print(f"\nSuccessfully processed files:")
            for result in output_results:
                if result.success and not result.user_skipped:
                    if result.output_path != result.file_path:
                        print(f"  - {result.file_path} -> {result.output_path}")
                    else:
                        print(f"  - {result.file_path}")

        print(f"{'='*50}")

    def cleanup_backup_files(self, directory: Path, pattern: str = "*.backup") -> int:
        """
        Clean up backup files in the specified directory.

        Args:
            directory: Directory to clean up
            pattern: Glob pattern for backup files

        Returns:
            Number of backup files removed
        """
        backup_files = list(directory.glob(pattern))
        removed_count = 0

        for backup_file in backup_files:
            try:
                backup_file.unlink()
                removed_count += 1
            except Exception:
                pass  # Ignore errors when cleaning up

        return removed_count