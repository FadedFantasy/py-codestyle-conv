"""
Module Mapper for Python Style Converter.
Handles mapping between file paths and Python module names.
"""

from typing import Dict, List
from pathlib import Path


class ModuleMapper:
    """Maps file paths to Python module names and vice versa."""

    def __init__(self, project_root: Path):
        """
        Initialize the module mapper.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root

    def build_module_mapping(self, file_paths: List[Path]) -> tuple[Dict[Path, str], Dict[str, Path]]:
        """
        Build mapping between file paths and Python module names.

        Args:
            file_paths: List of Python files to map

        Returns:
            Tuple of (file_to_module, module_to_file) dictionaries
        """
        file_to_module = {}
        module_to_file = {}

        for file_path in file_paths:
            module_name = self._file_path_to_module_name(file_path)
            file_to_module[file_path] = module_name
            module_to_file[module_name] = file_path

        return file_to_module, module_to_file

    def _file_path_to_module_name(self, file_path: Path) -> str:
        """
        Convert file path to module name.

        Args:
            file_path: Path to Python file

        Returns:
            Module name (e.g., 'package.module')
        """
        # Convert file path to module name
        relative_path = file_path.relative_to(self.project_root)

        # Remove .py extension and convert path separators to dots
        module_parts = list(relative_path.parts[:-1])  # Remove filename
        filename = relative_path.stem  # Filename without .py

        if filename != '__init__':
            module_parts.append(filename)

        module_name = '.'.join(module_parts) if module_parts else filename
        return module_name

    def get_module_name(self, file_path: Path) -> str:
        """
        Get module name for a specific file path.

        Args:
            file_path: Path to the file

        Returns:
            Module name
        """
        return self._file_path_to_module_name(file_path)