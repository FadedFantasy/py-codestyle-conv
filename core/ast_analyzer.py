"""
AST analyzer for Python Style Converter.
Provides analysis and transformation capabilities for Python source code using AST.
"""

import ast
import astor
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CodeElement:
    """Represents a code element that can be transformed."""
    name: str
    element_type: str  # 'variable', 'function', 'class', 'constant', etc.
    line_number: int
    column: int
    context: str  # Additional context about where the element is found
    node: ast.AST  # Reference to the AST node


@dataclass
class TransformationResult:
    """Result of a code transformation."""
    original_code: str
    transformed_code: str
    changes_made: List[str]
    elements_changed: List[CodeElement]


class ASTAnalyzer:
    """Analyzes and transforms Python code using Abstract Syntax Trees."""

    def __init__(self):
        """Initialize the AST analyzer."""
        self.original_source = None
        self.tree = None
        self.source_lines = None

    def load_file(self, file_path: Path) -> None:
        """
        Load and parse a Python file.

        Args:
            file_path: Path to the Python file to analyze
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.original_source = f.read()

            self.source_lines = self.original_source.splitlines()
            self.tree = ast.parse(self.original_source)

        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except UnicodeDecodeError:
            raise ValueError(f"File encoding not supported: {file_path}")
        except SyntaxError as e:
            raise SyntaxError(f"Syntax error in file {file_path}: {e}")

    def load_source(self, source_code: str) -> None:
        """
        Load and parse Python source code directly.

        Args:
            source_code: Python source code as string
        """
        try:
            self.original_source = source_code
            self.source_lines = source_code.splitlines()
            self.tree = ast.parse(source_code)
        except SyntaxError as e:
            raise SyntaxError(f"Syntax error in source code: {e}")

    def extract_code_elements(self) -> List[CodeElement]:
        """
        Extract all relevant code elements from the AST.

        Returns:
            List of CodeElement objects representing extractable elements
        """
        if not self.tree:
            raise ValueError("No AST loaded. Call load_file() or load_source() first.")

        elements = []

        class ElementVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.current_class = None
                self.current_function = None

            def visit_ClassDef(self, node):
                # Class definition
                elements.append(CodeElement(
                    name=node.name,
                    element_type='class',
                    line_number=node.lineno,
                    column=node.col_offset,
                    context='class_definition',
                    node=node
                ))

                old_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = old_class

            def visit_FunctionDef(self, node):
                # Function/method definition
                element_type = 'function'
                context = 'function_definition'

                if self.current_class:
                    element_type = 'method'
                    context = f'method_in_class_{self.current_class}'

                    # Determine if it's a private or dunder method
                    if node.name.startswith('__') and node.name.endswith('__'):
                        element_type = 'dunder_method'
                    elif node.name.startswith('_'):
                        element_type = 'private_method'

                elements.append(CodeElement(
                    name=node.name,
                    element_type=element_type,
                    line_number=node.lineno,
                    column=node.col_offset,
                    context=context,
                    node=node
                ))

                old_function = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = old_function

            def visit_AsyncFunctionDef(self, node):
                # Async function - treat same as regular function
                self.visit_FunctionDef(node)

            def visit_Assign(self, node):
                # Variable assignments
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        element_type = 'variable'

                        # Detect constants (all uppercase)
                        if target.id.isupper():
                            element_type = 'constant'

                        context = 'assignment'
                        if self.current_class:
                            context = f'assignment_in_class_{self.current_class}'
                        if self.current_function:
                            context = f'assignment_in_function_{self.current_function}'

                        elements.append(CodeElement(
                            name=target.id,
                            element_type=element_type,
                            line_number=target.lineno,
                            column=target.col_offset,
                            context=context,
                            node=target
                        ))

                self.generic_visit(node)

            def visit_AnnAssign(self, node):
                # Annotated assignments (type hints)
                if isinstance(node.target, ast.Name):
                    element_type = 'variable'

                    if node.target.id.isupper():
                        element_type = 'constant'

                    context = 'annotated_assignment'
                    if self.current_class:
                        context = f'annotated_assignment_in_class_{self.current_class}'
                    if self.current_function:
                        context = f'annotated_assignment_in_function_{self.current_function}'

                    elements.append(CodeElement(
                        name=node.target.id,
                        element_type=element_type,
                        line_number=node.target.lineno,
                        column=node.target.col_offset,
                        context=context,
                        node=node.target
                    ))

                self.generic_visit(node)

            def visit_Name(self, node):
                # Variable usage (not assignment)
                if isinstance(node.ctx, ast.Load):
                    # This is a variable being read, not assigned
                    # We might want to track these for comprehensive renaming
                    pass

                self.generic_visit(node)

        visitor = ElementVisitor(self)
        visitor.visit(self.tree)

        return elements

    def get_source_around_line(self, line_number: int, context_lines: int = 2) -> str:
        """
        Get source code around a specific line for context.

        Args:
            line_number: Line number (1-based)
            context_lines: Number of lines before and after to include

        Returns:
            Source code snippet with context
        """
        if not self.source_lines:
            return ""

        start = max(0, line_number - context_lines - 1)
        end = min(len(self.source_lines), line_number + context_lines)

        lines_with_numbers = []
        for i in range(start, end):
            marker = ">>> " if i == line_number - 1 else "    "
            lines_with_numbers.append(f"{marker}{i+1:3}: {self.source_lines[i]}")

        return "\n".join(lines_with_numbers)

    def apply_transformations(self, transformations: Dict[str, str]) -> str:
        """
        Apply name transformations to the AST and return modified source code.

        Args:
            transformations: Dictionary mapping old names to new names

        Returns:
            Transformed source code
        """
        if not self.tree:
            raise ValueError("No AST loaded. Call load_file() or load_source() first.")

        class NameTransformer(ast.NodeTransformer):
            def __init__(self, name_map):
                self.name_map = name_map

            def visit_Name(self, node):
                if node.id in self.name_map:
                    node.id = self.name_map[node.id]
                return node

            def visit_FunctionDef(self, node):
                if node.name in self.name_map:
                    node.name = self.name_map[node.name]
                return self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                if node.name in self.name_map:
                    node.name = self.name_map[node.name]
                return self.generic_visit(node)

            def visit_ClassDef(self, node):
                if node.name in self.name_map:
                    node.name = self.name_map[node.name]
                return self.generic_visit(node)

            def visit_Attribute(self, node):
                # Handle attribute access like obj.method_name
                if node.attr in self.name_map:
                    node.attr = self.name_map[node.attr]
                return self.generic_visit(node)

        transformer = NameTransformer(transformations)
        new_tree = transformer.visit(self.tree)

        # Convert back to source code with formatting preservation
        try:
            # Use astor with options to preserve formatting as much as possible
            return astor.to_source(new_tree,
                                 indent_with=' ' * 4,  # Use 4 spaces for indentation
                                 add_line_information=False,  # Don't add line info comments
                                 pretty_source=lambda x: ''.join(x)  # Minimize formatting changes
                                )
        except Exception as e:
            # Fallback: try with default settings
            try:
                return astor.to_source(new_tree)
            except Exception as e2:
                raise ValueError(f"Error converting AST back to source: {e2}")

    def apply_transformations_preserve_formatting(self, transformations: Dict[str, str]) -> str:
        """
        Apply name transformations while preserving original formatting as much as possible.
        This is a more conservative approach that tries to keep the original structure.

        Args:
            transformations: Dictionary mapping old names to new names

        Returns:
            Transformed source code with minimal formatting changes
        """
        if not transformations:
            return self.original_source

        # Use a simple string replacement approach for better formatting preservation
        result = self.original_source

        # Sort transformations by length (longer first) to avoid partial replacements
        sorted_transformations = sorted(transformations.items(), key=lambda x: len(x[0]), reverse=True)

        for old_name, new_name in sorted_transformations:
            # Use word boundary regex to replace only complete identifiers
            # This handles: variable names, function names, class names, attribute access

            # Pattern to match the identifier as a complete word
            pattern = rf'\b{re.escape(old_name)}\b'
            result = re.sub(pattern, new_name, result)

            # Also handle attribute access (after dots)
            attr_pattern = rf'\.{re.escape(old_name)}\b'
            attr_replacement = f'.{new_name}'
            result = re.sub(attr_pattern, attr_replacement, result)

        return result

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

    def get_imports(self) -> List[Tuple[str, Optional[str]]]:
        """
        Get all import statements from the AST.

        Returns:
            List of tuples (module_name, alias) for imports
        """
        if not self.tree:
            return []

        imports = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, alias.asname))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    imports.append((full_name, alias.asname))

        return imports

    def get_line_length_violations(self, max_length: int) -> List[Tuple[int, int, str]]:
        """
        Find lines that exceed the maximum length.

        Args:
            max_length: Maximum allowed line length

        Returns:
            List of tuples (line_number, actual_length, line_content)
        """
        if not self.source_lines:
            return []

        violations = []
        for i, line in enumerate(self.source_lines, 1):
            if len(line) > max_length:
                violations.append((i, len(line), line))

        return violations