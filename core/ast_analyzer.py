"""
AST analyzer for Python Style Converter.
Simplified orchestrator that coordinates AST parsing, element extraction, and transformations.
Formatting-related functionality removed except for what's needed for blank lines.
"""

import ast
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path

from .ast_parser import ASTParser, ParseResult
from .code_element_extractor import CodeElementExtractor, CodeElement
from .code_transformer import CodeTransformer, TransformationResult


class ASTAnalyzer:
    """Simplified AST analyzer that orchestrates parsing, extraction, and transformation."""

    def __init__(self):
        """Initialize the AST analyzer."""
        self.parser = ASTParser()
        self.extractor = CodeElementExtractor()
        self.transformer = CodeTransformer()

        # Current state
        self.current_parse_result: Optional[ParseResult] = None

    def load_file(self, file_path: Path) -> None:
        """
        Load and parse a Python file.

        Args:
            file_path: Path to the Python file to analyze

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file encoding not supported
            SyntaxError: If file has syntax errors
        """
        parse_result = self.parser.parse_file(file_path)

        if not parse_result.success:
            if "not found" in parse_result.error_message:
                raise FileNotFoundError(parse_result.error_message)
            elif "encoding" in parse_result.error_message:
                raise ValueError(parse_result.error_message)
            else:
                raise SyntaxError(parse_result.error_message)

        self.current_parse_result = parse_result

    def load_source(self, source_code: str) -> None:
        """
        Load and parse Python source code directly.

        Args:
            source_code: Python source code as string

        Raises:
            SyntaxError: If source code has syntax errors
        """
        parse_result = self.parser.parse_source(source_code)

        if not parse_result.success:
            raise SyntaxError(parse_result.error_message)

        self.current_parse_result = parse_result

    @property
    def original_source(self) -> str:
        """Get the original source code."""
        if not self.current_parse_result:
            raise ValueError("No source loaded. Call load_file() or load_source() first.")
        return self.current_parse_result.source_code

    @property
    def tree(self) -> ast.AST:
        """Get the AST tree."""
        if not self.current_parse_result:
            raise ValueError("No AST loaded. Call load_file() or load_source() first.")
        return self.current_parse_result.tree

    def extract_code_elements(self) -> List[CodeElement]:
        """
        Extract all relevant code elements from the AST.

        Returns:
            List of CodeElement objects representing extractable elements

        Raises:
            ValueError: If no AST is loaded
        """
        if not self.current_parse_result:
            raise ValueError("No AST loaded. Call load_file() or load_source() first.")

        return self.extractor.extract_elements(self.current_parse_result.tree)

    def get_source_around_line(self, line_number: int, context_lines: int = 2) -> str:
        """
        Get source code around a specific line for context.

        Args:
            line_number: Line number (1-based)
            context_lines: Number of lines before and after to include

        Returns:
            Source code snippet with context
        """
        return self.parser.get_source_around_line(line_number, context_lines)

    def apply_transformations(self, transformations: Dict[str, str]) -> str:
        """
        Apply name transformations to the AST and return modified source code.

        Args:
            transformations: Dictionary mapping old names to new names

        Returns:
            Transformed source code

        Raises:
            ValueError: If no AST is loaded or transformation fails
        """
        if not self.current_parse_result:
            raise ValueError("No AST loaded. Call load_file() or load_source() first.")

        return self.transformer.apply_transformations(
            self.current_parse_result.tree,
            self.current_parse_result.source_code,
            transformations
        )

    def apply_transformations_preserve_formatting(self, transformations: Dict[str, str]) -> str:
        """
        Apply name transformations while preserving original formatting as much as possible.

        Args:
            transformations: Dictionary mapping old names to new names

        Returns:
            Transformed source code with minimal formatting changes

        Raises:
            ValueError: If no source is loaded
        """
        if not self.current_parse_result:
            raise ValueError("No source loaded. Call load_file() or load_source() first.")

        return self.transformer.apply_transformations_preserve_formatting(
            self.current_parse_result.source_code,
            transformations
        )

    def validate_syntax(self, source_code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that source code has valid Python syntax.

        Args:
            source_code: Python source code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.parser.validate_syntax(source_code)

    def get_imports(self) -> List[Tuple[str, Optional[str]]]:
        """
        Get all import statements from the AST.

        Returns:
            List of tuples (module_name, alias) for imports

        Raises:
            ValueError: If no AST is loaded
        """
        if not self.current_parse_result:
            return []

        return self.parser.get_imports(self.current_parse_result.tree)