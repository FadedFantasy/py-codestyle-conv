"""
Docstring Formatter for Python Style Converter.
Handles formatting of docstrings according to Google style guidelines.
"""

import ast
import re
from typing import Optional, List, Tuple
from dataclasses import dataclass

from config.config_manager import ConfigManager


@dataclass
class DocstringChange:
    """Represents a change made to a docstring."""
    line_number: int
    old_content: str
    new_content: str
    change_type: str  # 'formatting', 'capitalization', 'punctuation'


class DocstringFormatter:
    """Handles docstring formatting according to Google style guidelines."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the docstring formatter.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config = config_manager

    def is_formatting_enabled(self) -> bool:
        """Check if docstring formatting rule is enabled."""
        return self.config.is_rule_enabled('docstring_formatting')

    def apply_docstring_formatting(self, source_code: str) -> Tuple[Optional[str], List[str]]:
        """
        Apply docstring formatting to source code.

        Args:
            source_code: Source code to format

        Returns:
            Tuple of (formatted_source_code, list_of_changes_made)
            Returns (None, []) if no changes needed
        """
        if not self.is_formatting_enabled():
            return None, []

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return None, []

        changes_made = []
        formatted_source = source_code

        # Find all docstrings and format them using regex replacement
        docstring_nodes = self._find_docstrings(tree)

        for node in docstring_nodes:
            if self._is_docstring_node(node):
                old_docstring = self._get_docstring_content(node)
                new_docstring = self._format_docstring(old_docstring)

                if new_docstring != old_docstring:
                    # Use regex to replace the docstring in the source
                    formatted_source = self._replace_docstring_with_regex(
                        formatted_source, old_docstring, new_docstring
                    )

                    # Track the change
                    change_description = self._describe_change(old_docstring, new_docstring, node.lineno)
                    changes_made.append(change_description)

        if formatted_source != source_code:
            return formatted_source, changes_made
        else:
            return None, []

    def _find_docstrings(self, tree: ast.AST) -> List[ast.Constant]:
        """Find all potential docstring nodes in the AST."""
        docstring_nodes = []

        class DocstringVisitor(ast.NodeVisitor):
            def __init__(self):
                self.in_function = False
                self.in_class = False

            def visit_Module(self, node):
                # Module-level docstring
                if (node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Str, ast.Constant))):
                    docstring_nodes.append(node.body[0].value)
                self.generic_visit(node)

            def visit_FunctionDef(self, node):
                # Function docstring
                if (node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Str, ast.Constant))):
                    docstring_nodes.append(node.body[0].value)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                # Async function docstring
                self.visit_FunctionDef(node)

            def visit_ClassDef(self, node):
                # Class docstring
                if (node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Str, ast.Constant))):
                    docstring_nodes.append(node.body[0].value)
                self.generic_visit(node)

        visitor = DocstringVisitor()
        visitor.visit(tree)
        return docstring_nodes

    def _is_docstring_node(self, node: ast.AST) -> bool:
        """Check if a node represents a docstring."""
        if isinstance(node, ast.Str):  # Python < 3.8
            return isinstance(node.s, str)
        elif isinstance(node, ast.Constant):  # Python >= 3.8
            return isinstance(node.value, str)
        return False

    def _get_docstring_content(self, node: ast.AST) -> str:
        """Get the string content from a docstring node."""
        if isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        elif isinstance(node, ast.Constant):  # Python >= 3.8
            return node.value
        return ""

    def _format_docstring(self, docstring: str) -> str:
        """
        Format a docstring according to Google style guidelines.

        Args:
            docstring: Original docstring content

        Returns:
            Formatted docstring content
        """
        if not docstring or not docstring.strip():
            return docstring

        # Determine if this is a one-liner or multi-liner
        lines = docstring.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]

        if len(non_empty_lines) <= 1:
            # One-liner formatting
            return self._format_one_liner(docstring)
        else:
            # Multi-liner formatting
            return self._format_multi_liner(docstring)

    def _format_one_liner(self, docstring: str) -> str:
        """Format a one-line docstring."""
        # Remove leading/trailing whitespace
        content = docstring.strip()

        if not content:
            return docstring

        # Capitalize first letter
        if content and content[0].islower():
            content = content[0].upper() + content[1:]

        # Ensure it ends with a period
        if content and not content.endswith('.'):
            content += '.'

        return content

    def _format_multi_liner(self, docstring: str) -> str:
        """Format a multi-line docstring."""
        lines = docstring.split('\n')

        # Find the summary line (first non-empty line)
        summary_idx = -1
        for i, line in enumerate(lines):
            if line.strip():
                summary_idx = i
                break

        if summary_idx == -1:
            return docstring  # No content

        # Extract and format the summary
        summary = lines[summary_idx].strip()

        # Don't modify lines that contain Args:, Returns:, Yields:, etc.
        if self._is_section_header(summary):
            return docstring

        # Capitalize first letter of summary
        if summary and summary[0].islower():
            summary = summary[0].upper() + summary[1:]

        # Ensure summary ends with a period
        if summary and not summary.endswith('.'):
            summary += '.'

        # Rebuild the docstring
        new_lines = lines[:]
        new_lines[summary_idx] = summary

        return '\n'.join(new_lines)

    def _is_section_header(self, line: str) -> bool:
        """Check if a line is a docstring section header like Args:, Returns:, etc."""
        line = line.strip()
        section_headers = [
            'Args:', 'Arguments:', 'Parameters:',
            'Returns:', 'Return:', 'Yields:', 'Yield:',
            'Raises:', 'Except:', 'Exceptions:',
            'Note:', 'Notes:', 'Example:', 'Examples:',
            'See Also:', 'References:', 'Todo:', 'Warning:', 'Warnings:'
        ]
        return any(line.startswith(header) for header in section_headers)

    def _replace_docstring_with_regex(self, source_code: str, old_docstring: str, new_docstring: str) -> str:
        """
        Replace docstring content using regex - simpler and more reliable for GUI highlighting.

        Args:
            source_code: Full source code
            old_docstring: Original docstring content
            new_docstring: New formatted docstring content

        Returns:
            Updated source code
        """
        # Escape special regex characters in the old docstring
        escaped_old = re.escape(old_docstring)

        # Handle both triple quote styles
        patterns = [
            # Triple double quotes - one line: """content"""
            rf'("""){escaped_old}(""")',
            # Triple single quotes - one line: '''content'''
            rf"('''){escaped_old}(''')",
            # Triple double quotes - multi line: """\ncontent\n"""
            rf'("""\s*){escaped_old}(\s*""")',
            # Triple single quotes - multi line: '''\ncontent\n'''
            rf"('''\s*){escaped_old}(\s*''')",
        ]

        for pattern in patterns:
            if re.search(pattern, source_code, re.DOTALL):
                # Replace with new content, preserving the quote style and basic structure
                replacement = rf'\1{new_docstring}\2'
                return re.sub(pattern, replacement, source_code, count=1, flags=re.DOTALL)

        # If no pattern matched, return original (this shouldn't happen normally)
        return source_code

    def _describe_change(self, old_docstring: str, new_docstring: str, line_number: int) -> str:
        """Create a human-readable description of the docstring change."""
        changes = []

        old_stripped = old_docstring.strip()
        new_stripped = new_docstring.strip()

        # Check for capitalization changes
        if (old_stripped and new_stripped and
            old_stripped[0] != new_stripped[0] and
            old_stripped[0].islower() and new_stripped[0].isupper()):
            changes.append("capitalized first letter")

        # Check for punctuation changes
        if (old_stripped and new_stripped and
            not old_stripped.endswith('.') and new_stripped.endswith('.')):
            changes.append("added period")

        # Check for whitespace trimming
        if old_docstring != old_stripped:
            changes.append("trimmed whitespace")

        if changes:
            change_desc = " and ".join(changes)
            return f"Formatted docstring at line {line_number}: {change_desc}"
        else:
            return f"Formatted docstring at line {line_number}"