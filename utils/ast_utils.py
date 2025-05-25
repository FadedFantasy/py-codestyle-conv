"""
AST utility functions for Python Style Converter.
Provides helper functions for working with Python Abstract Syntax Trees.
"""

import ast
from typing import List, Dict, Set, Optional, Any, Tuple, Union


class ASTHelper:
    """Helper class for AST operations."""

    @staticmethod
    def find_all_names(tree: ast.AST) -> Set[str]:
        """
        Find all name identifiers in an AST.

        Args:
            tree: AST to search

        Returns:
            Set of all identifier names found
        """
        names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.FunctionDef):
                names.add(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                names.add(node.name)

        return names

    @staticmethod
    def find_function_definitions(tree: ast.AST) -> List[ast.FunctionDef]:
        """
        Find all function definitions in an AST.

        Args:
            tree: AST to search

        Returns:
            List of FunctionDef nodes
        """
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node)

        return functions

    @staticmethod
    def find_class_definitions(tree: ast.AST) -> List[ast.ClassDef]:
        """
        Find all class definitions in an AST.

        Args:
            tree: AST to search

        Returns:
            List of ClassDef nodes
        """
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node)

        return classes

    @staticmethod
    def find_variable_assignments(tree: ast.AST) -> List[ast.Assign]:
        """
        Find all variable assignments in an AST.

        Args:
            tree: AST to search

        Returns:
            List of Assign nodes
        """
        assignments = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                assignments.append(node)

        return assignments

    @staticmethod
    def get_node_name(node: ast.AST) -> Optional[str]:
        """
        Get the name of an AST node if it has one.

        Args:
            node: AST node to get name from

        Returns:
            Name string if node has a name, None otherwise
        """
        if hasattr(node, 'name'):
            return node.name
        elif hasattr(node, 'id'):
            return node.id
        else:
            return None

    @staticmethod
    def is_private_name(name: str) -> bool:
        """
        Check if a name follows Python private naming convention.

        Args:
            name: Name to check

        Returns:
            True if name is private (starts with underscore)
        """
        return name.startswith('_') and not name.startswith('__')

    @staticmethod
    def is_dunder_name(name: str) -> bool:
        """
        Check if a name follows Python dunder naming convention.

        Args:
            name: Name to check

        Returns:
            True if name is dunder (starts and ends with double underscore)
        """
        return name.startswith('__') and name.endswith('__') and len(name) > 4

    @staticmethod
    def is_constant_name(name: str) -> bool:
        """
        Check if a name follows Python constant naming convention.

        Args:
            name: Name to check

        Returns:
            True if name appears to be a constant (all uppercase)
        """
        return name.isupper() and ('_' in name or name.isalpha())

    @staticmethod
    def get_function_scope(tree: ast.AST, target_function: str) -> Optional[ast.FunctionDef]:
        """
        Find a specific function definition by name.

        Args:
            tree: AST to search
            target_function: Name of function to find

        Returns:
            FunctionDef node if found, None otherwise
        """
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == target_function:
                    return node
        return None

    @staticmethod
    def get_class_scope(tree: ast.AST, target_class: str) -> Optional[ast.ClassDef]:
        """
        Find a specific class definition by name.

        Args:
            tree: AST to search
            target_class: Name of class to find

        Returns:
            ClassDef node if found, None otherwise
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name == target_class:
                    return node
        return None

    @staticmethod
    def get_imports(tree: ast.AST) -> List[Tuple[str, Optional[str]]]:
        """
        Get all import statements from an AST.

        Args:
            tree: AST to analyze

        Returns:
            List of tuples (module_name, alias) for each import
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

    @staticmethod
    def find_string_literals(tree: ast.AST) -> List[str]:
        """
        Find all string literals in an AST.

        Args:
            tree: AST to search

        Returns:
            List of string literal values
        """
        strings = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Str):  # Python < 3.8
                strings.append(node.s)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):  # Python >= 3.8
                strings.append(node.value)

        return strings

    @staticmethod
    def has_decorator(func_node: ast.FunctionDef, decorator_name: str) -> bool:
        """
        Check if a function has a specific decorator.

        Args:
            func_node: FunctionDef node to check
            decorator_name: Name of decorator to look for

        Returns:
            True if function has the decorator, False otherwise
        """
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == decorator_name:
                return True
            elif isinstance(decorator, ast.Attribute) and decorator.attr == decorator_name:
                return True
        return False

    @staticmethod
    def get_node_line_range(node: ast.AST) -> Tuple[int, int]:
        """
        Get the line range (start, end) of an AST node.

        Args:
            node: AST node

        Returns:
            Tuple of (start_line, end_line)
        """
        start_line = getattr(node, 'lineno', 0)

        # Try to get end line from various attributes
        end_line = start_line
        if hasattr(node, 'end_lineno') and node.end_lineno:
            end_line = node.end_lineno
        elif hasattr(node, 'body') and node.body:
            # For compound statements, find the last line of the body
            last_stmt = node.body[-1]
            if hasattr(last_stmt, 'lineno'):
                end_line = last_stmt.lineno

        return start_line, end_line

    @staticmethod
    def is_method_in_class(tree: ast.AST, method_name: str, class_name: str) -> bool:
        """
        Check if a method exists within a specific class.

        Args:
            tree: AST to search
            method_name: Name of method to find
            class_name: Name of class to search in

        Returns:
            True if method exists in the class, False otherwise
        """
        class_node = ASTHelper.get_class_scope(tree, class_name)
        if not class_node:
            return False

        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == method_name:
                    return True

        return False

    @staticmethod
    def count_complexity(tree: ast.AST) -> int:
        """
        Calculate a simple complexity metric for an AST.

        Args:
            tree: AST to analyze

        Returns:
            Complexity score (higher = more complex)
        """
        complexity = 0

        for node in ast.walk(tree):
            # Count decision points
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity += 1
            elif isinstance(node, ast.ClassDef):
                complexity += 1

        return complexity

    @staticmethod
    def validate_identifier(name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a string is a valid Python identifier.

        Args:
            name: String to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, "Name cannot be empty"

        if not name.isidentifier():
            return False, f"'{name}' is not a valid Python identifier"

        # Check against Python keywords
        import keyword
        if keyword.iskeyword(name):
            return False, f"'{name}' is a Python keyword"

        return True, None