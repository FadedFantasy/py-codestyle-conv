"""
File Writer for Python Style Converter.
Handles writing transformed code to files (in-place or new files).
"""

import shutil
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from config.config_manager import ConfigManager


@dataclass
class WriteResult:
    """Result of writing a file."""
    success: bool
    output_path: Optional[Path]
    error_message: Optional[str] = None


class FileWriter:
    """Handles writing transformed code to files."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize FileWriter with configuration.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config = config_manager
        self.output_mode = config_manager.get_output_mode()
        self.new_files_suffix = config_manager.get_new_files_suffix()

    def write_transformed_code(self, file_path: Path, transformed_code: str) -> WriteResult:
        """
        Write transformed code to file according to configuration.

        Args:
            file_path: Original file path
            transformed_code: Transformed code to write

        Returns:
            WriteResult with operation result
        """
        try:
            if self.output_mode == "in_place":
                output_path = self._write_in_place(file_path, transformed_code)
            elif self.output_mode == "new_files":
                output_path = self._write_new_file(file_path, transformed_code)
            else:
                return WriteResult(
                    success=False,
                    output_path=None,
                    error_message=f"Unknown output mode: {self.output_mode}"
                )

            return WriteResult(
                success=True,
                output_path=output_path
            )

        except Exception as e:
            return WriteResult(
                success=False,
                output_path=None,
                error_message=str(e)
            )

    def _write_in_place(self, file_path: Path, transformed_code: str) -> Path:
        """
        Write changes back to original file with backup.

        Args:
            file_path: Original file path
            transformed_code: Code to write

        Returns:
            Path to the written file
        """
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        shutil.copy2(file_path, backup_path)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(transformed_code)
            backup_path.unlink()  # Remove backup if successful
            return file_path
        except Exception as e:
            # Restore from backup if write failed
            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
                backup_path.unlink()
            raise e

    def _write_new_file(self, original_path: Path, transformed_code: str) -> Path:
        """
        Write changes to new file with suffix.

        Args:
            original_path: Original file path
            transformed_code: Code to write

        Returns:
            Path to the new file
        """
        stem = original_path.stem
        suffix = original_path.suffix

        new_filename = f"{stem}{self.new_files_suffix}{suffix}"
        new_path = original_path.parent / new_filename

        # Handle filename conflicts
        counter = 1
        while new_path.exists():
            new_filename = f"{stem}{self.new_files_suffix}_{counter}{suffix}"
            new_path = original_path.parent / new_filename
            counter += 1

        with open(new_path, 'w', encoding='utf-8') as f:
            f.write(transformed_code)

        return new_path