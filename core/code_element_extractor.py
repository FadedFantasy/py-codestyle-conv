"""
Code Element Extractor for Python Style Converter.
Extracts code elements (classes, functions, variables, etc.) from AST trees.
"""

import ast
from typing import List
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


class CodeElementExtractor:
    """Extracts code elements from AST trees."""

    def __init__(self):
        """Initialize the code element extractor."""
        pass

    def extract_elements(self, tree: ast.AST) -> List[CodeElement]:
        """
        Extract all relevant code elements from the AST.

        Args:
            tree: AST tree to analyze

        Returns:
            List of CodeElement objects representing extractable elements
        """
        elements = []

        class ElementVisitor(ast.NodeVisitor):
            def __init__(self, extractor):
                self.extractor = extractor
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

                        # Detect constants - either all uppercase OR module-level literal assignments
                        if target.id.isupper():
                            element_type = 'constant'
                        elif self._is_module_level_literal_assignment(node):
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

                    # Detect constants - either all uppercase OR module-level literal assignments
                    if node.target.id.isupper():
                        element_type = 'constant'
                    elif self._is_module_level_literal_assignment(node):
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

            def _is_module_level_literal_assignment(self, node):
                """Check if this is a module-level assignment to a literal value."""
                # Check if we're at module level (not inside class or function)
                if self.current_class or self.current_function:
                    return False

                # Check if the value is a literal
                if hasattr(node, 'value'):  # ast.Assign
                    return self._is_literal_value(node.value)
                elif hasattr(node, 'value') and node.value is not None:  # ast.AnnAssign with value
                    return self._is_literal_value(node.value)

                return False

            def _is_literal_value(self, node):
                """Check if a node represents a literal value."""
                # Handle Python 3.8+ ast.Constant
                if isinstance(node, ast.Constant):
                    return isinstance(node.value, (int, float, str, bool, type(None)))

                # Handle older Python versions
                if isinstance(node, ast.Num):  # Numbers
                    return True
                elif isinstance(node, ast.Str):  # Strings
                    return True
                elif isinstance(node, ast.NameConstant):  # True, False, None
                    return True
                elif isinstance(node, ast.Name) and node.id in ('True', 'False', 'None'):
                    return True

                # Could extend to handle simple collections like [1, 2, 3] or {'key': 'value'}
                # but keeping it simple for now

                return False

        visitor = ElementVisitor(self)
        visitor.visit(tree)

        return elements