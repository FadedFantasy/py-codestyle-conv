"""
Code Transformer for Python Style Converter.
Handles applying transformations to AST trees and source code.
"""

import ast
import astor
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from .code_element_extractor import CodeElement


@dataclass
class TransformationResult:
    """Result of a code transformation."""
    original_code: str
    transformed_code: str
    changes_made: List[str]
    elements_changed: List[CodeElement]


class CodeTransformer:
    """Handles code transformations using AST manipulation."""

    def __init__(self):
        """Initialize the code transformer."""
        pass

    def apply_transformations(self, tree: ast.AST, source_code: str, transformations: Dict[str, str]) -> str:
        """
        Apply name transformations to the AST and return modified source code.

        Args:
            tree: AST tree to transform
            source_code: Original source code
            transformations: Dictionary mapping old names to new names

        Returns:
            Transformed source code
        """
        if not transformations:
            return source_code

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
        new_tree = transformer.visit(tree)

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

    def apply_transformations_preserve_formatting(self, source_code: str, transformations: Dict[str, str]) -> str:
        """
        Apply name transformations while preserving original formatting as much as possible.
        This is a more conservative approach that tries to keep the original structure.

        Args:
            source_code: Original source code
            transformations: Dictionary mapping old names to new names

        Returns:
            Transformed source code with minimal formatting changes
        """
        if not transformations:
            return source_code

        # Use a simple string replacement approach for better formatting preservation
        result = source_code

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

    def create_transformation_result(self,
                                   original_code: str,
                                   transformed_code: str,
                                   changes_made: List[str],
                                   elements_changed: List[CodeElement]) -> TransformationResult:
        """
        Create a TransformationResult object.

        Args:
            original_code: Original source code
            transformed_code: Transformed source code
            changes_made: List of human-readable changes
            elements_changed: List of CodeElement objects that were changed

        Returns:
            TransformationResult object
        """
        return TransformationResult(
            original_code=original_code,
            transformed_code=transformed_code,
            changes_made=changes_made,
            elements_changed=elements_changed
        )