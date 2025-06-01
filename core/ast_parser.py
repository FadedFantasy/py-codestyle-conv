"""
AST Parser for Python Style Converter.
Handles loading and parsing Python source code into AST trees.
"""

import ast
from typing import List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ParseResult:
    """Result of parsing a Python file."""
    tree: ast.AST
    source_code: str
    source_lines: List[str]
    success: bool
    error_message: Optional[str] = None


class ASTParser:
    """Parses Python source code into AST trees."""

    def __init__(self):
        """Initialize the AST parser."""
        self.current_result: Optional[ParseResult] = None

    def parse_file(self, file_path: Path) -> ParseResult:
        """
        Load and parse a Python file.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            ParseResult with parsing information
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            return self.parse_source(source_code)

        except FileNotFoundError:
            return ParseResult(
                tree=None,
                source_code="",
                source_lines=[],
                success=False,
                error_message=f"File not found: {file_path}"
            )
        except UnicodeDecodeError:
            return ParseResult(
                tree=None,
                source_code="",
                source_lines=[],
                success=False,
                error_message=f"File encoding not supported: {file_path}"
            )

    def parse_source(self, source_code: str) -> ParseResult:
        """
        Load and parse Python source code directly.

        Args:
            source_code: Python source code as string

        Returns:
            ParseResult with parsing information
        """
        try:
            source_lines = source_code.splitlines()
            tree = ast.parse(source_code)

            result = ParseResult(
                tree=tree,
                source_code=source_code,
                source_lines=source_lines,
                success=True
            )

            self.current_result = result
            return result

        except SyntaxError as e:
            return ParseResult(
                tree=None,
                source_code=source_code,
                source_lines=source_code.splitlines(),
                success=False,
                error_message=f"Syntax error in source code: {e}"
            )

    def get_source_around_line(self, line_number: int, context_lines: int = 2) -> str:
        """
        Get source code around a specific line for context.

        Args:
            line_number: Line number (1-based)
            context_lines: Number of lines before and after to include

        Returns:
            Source code snippet with context
        """
        if not self.current_result or not self.current_result.source_lines:
            return ""

        source_lines = self.current_result.source_lines
        start = max(0, line_number - context_lines - 1)
        end = min(len(source_lines), line_number + context_lines)

        lines_with_numbers = []
        for i in range(start, end):
            marker = ">>> " if i == line_number - 1 else "    "
            lines_with_numbers.append(f"{marker}{i+1:3}: {source_lines[i]}")

        return "\n".join(lines_with_numbers)

    def validate_syntax(self, source_code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that source code has valid Python syntax.

        Args:
            source_code: Python source code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ast.parse(source_code)
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def get_imports(self, tree: ast.AST) -> List[Tuple[str, Optional[str]]]:
        """
        Get all import statements from an AST.

        Args:
            tree: AST to analyze

        Returns:
            List of tuples (module_name, alias) for imports
        """
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, alias.asname))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    imports.append((full_name, alias.asname))

        return imports