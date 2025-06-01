"""
Blank Lines Formatter for Python Style Converter.
Handles the remaining formatting functionality - adding blank lines after classes and functions.
"""

from typing import Optional

from config.config_manager import ConfigManager


class BlankLinesFormatter:
    """Handles blank lines formatting for classes and functions."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the blank lines formatter.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config = config_manager

    def is_formatting_enabled(self) -> bool:
        """Check if blank lines formatting rule is enabled."""
        return self.config.is_rule_enabled('blank_lines')

    def apply_blank_lines_formatting(self, source_code: str) -> Optional[str]:
        """
        Apply blank lines formatting to source code.

        Args:
            source_code: Source code to format

        Returns:
            Formatted source code if formatting is applied, None if no changes
        """
        # Only apply blank lines formatting if enabled
        if not self.is_formatting_enabled():
            return None

        formatted = self._add_blank_lines(source_code)
        if formatted != source_code:
            return formatted

        return None

    def _add_blank_lines(self, source_code: str) -> str:
        """
        Add blank lines after class and function definitions.

        Args:
            source_code: Source code to format

        Returns:
            Source code with blank lines added
        """
        lines = source_code.split('\n')
        formatted_lines = []

        # This is a simplified implementation
        # You'd want to use AST to properly identify class/function boundaries
        # But for now, using regex patterns for simplicity

        for i, line in enumerate(lines):
            formatted_lines.append(line)

            # Add blank lines after class definitions
            if line.strip().startswith('class ') and line.strip().endswith(':'):
                blank_lines = self.config.get_blank_lines_after_class()
                for _ in range(blank_lines):
                    formatted_lines.append('')

            # Add blank lines after function definitions
            elif line.strip().startswith('def ') and line.strip().endswith(':'):
                blank_lines = self.config.get_blank_lines_after_function()
                for _ in range(blank_lines):
                    formatted_lines.append('')

            # Also handle async functions
            elif line.strip().startswith('async def ') and line.strip().endswith(':'):
                blank_lines = self.config.get_blank_lines_after_function()
                for _ in range(blank_lines):
                    formatted_lines.append('')

        return '\n'.join(formatted_lines)