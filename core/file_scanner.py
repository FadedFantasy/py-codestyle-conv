"""
File scanner for Python Style Converter.
Handles recursive file discovery based on include/exclude patterns.
"""

import os
import fnmatch
from pathlib import Path
from typing import List, Set, Generator
from config.config_manager import ConfigManager


class FileScanner:
    """Scans directories for Python files based on configuration patterns."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize FileScanner with configuration.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config = config_manager
        self.include_patterns = config_manager.get_include_patterns()
        self.exclude_patterns = config_manager.get_exclude_patterns()
        self.recursive = config_manager.is_recursive()

    def scan_directory(self, directory: str) -> List[Path]:
        """
        Scan directory for Python files matching the configured patterns.

        Args:
            directory: Path to directory to scan

        Returns:
            List of Path objects for matching files
        """
        directory_path = Path(directory).resolve()

        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        found_files = []

        if self.recursive:
            for file_path in self._scan_recursive(directory_path):
                if self._should_include_file(file_path):
                    found_files.append(file_path)
        else:
            for file_path in directory_path.iterdir():
                if file_path.is_file() and self._should_include_file(file_path):
                    found_files.append(file_path)

        return sorted(found_files)

    def scan_file(self, file_path: str) -> List[Path]:
        """
        Process a single file if it matches patterns.

        Args:
            file_path: Path to the file to check

        Returns:
            List containing the file path if it matches, empty list otherwise
        """
        file_path_obj = Path(file_path).resolve()

        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path_obj.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        if self._should_include_file(file_path_obj):
            return [file_path_obj]
        else:
            return []

    def _scan_recursive(self, directory: Path) -> Generator[Path, None, None]:
        """
        Recursively scan directory for files.

        Args:
            directory: Directory to scan

        Yields:
            Path objects for all files found
        """
        try:
            for item in directory.iterdir():
                if item.is_file():
                    yield item
                elif item.is_dir() and not self._should_exclude_directory(item):
                    yield from self._scan_recursive(item)
        except PermissionError:
            # Skip directories we can't read
            pass

    def _should_include_file(self, file_path: Path) -> bool:
        """
        Check if file should be included based on patterns.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file should be included, False otherwise
        """
        # Check if file matches any exclude patterns first
        if self._matches_any_pattern(file_path, self.exclude_patterns):
            return False

        # Check if file matches any include patterns
        return self._matches_any_pattern(file_path, self.include_patterns)

    def _should_exclude_directory(self, dir_path: Path) -> bool:
        """
        Check if directory should be excluded from scanning.

        Args:
            dir_path: Path to the directory to check

        Returns:
            True if directory should be excluded, False otherwise
        """
        return self._matches_any_pattern(dir_path, self.exclude_patterns)

    def _matches_any_pattern(self, path: Path, patterns: List[str]) -> bool:
        """
        Check if path matches any of the given patterns.

        Args:
            path: Path to check
            patterns: List of glob patterns

        Returns:
            True if path matches any pattern, False otherwise
        """
        if not patterns:
            return False

        # Convert path to string for pattern matching
        path_str = str(path)
        path_name = path.name

        for pattern in patterns:
            # Check against full path
            if fnmatch.fnmatch(path_str, pattern):
                return True

            # Check against just filename
            if fnmatch.fnmatch(path_name, pattern):
                return True

            # Check against relative path parts
            path_parts = path.parts
            for i in range(len(path_parts)):
                partial_path = '/'.join(path_parts[i:])
                if fnmatch.fnmatch(partial_path, pattern):
                    return True

        return False

    def get_file_count_estimate(self, directory: str) -> int:
        """
        Get an estimate of how many files would be processed.

        Args:
            directory: Directory to estimate for

        Returns:
            Estimated number of files that would be processed
        """
        try:
            files = self.scan_directory(directory)
            return len(files)
        except Exception:
            return 0

    def validate_patterns(self) -> List[str]:
        """
        Validate that the configured patterns are valid.

        Returns:
            List of validation error messages (empty if all patterns are valid)
        """
        errors = []

        # Basic validation - check for obviously invalid patterns
        all_patterns = self.include_patterns + self.exclude_patterns

        for pattern in all_patterns:
            if not isinstance(pattern, str):
                errors.append(f"Pattern must be string: {pattern}")
            elif len(pattern.strip()) == 0:
                errors.append("Empty pattern found")

        return errors