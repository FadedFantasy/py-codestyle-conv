"""
Rule engine for Python Style Converter.
Orchestrates all code transformations based on configuration.
"""

from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import re

from config.config_manager import ConfigManager
from .ast_analyzer import ASTAnalyzer, CodeElement, TransformationResult


@dataclass
class ProcessingResult:
    """Result of processing a single file."""
    file_path: Path
    success: bool
    original_code: str
    transformed_code: Optional[str]
    changes_made: List[str]
    error_message: Optional[str]


class RuleEngine:
    """Main engine that applies all transformation rules to Python code."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize RuleEngine with configuration.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config = config_manager
        self.analyzer = ASTAnalyzer()

    def process_file(self, file_path: Path) -> ProcessingResult:
        """
        Process a single Python file according to configuration.

        Args:
            file_path: Path to the Python file to process

        Returns:
            ProcessingResult with transformation results
        """
        try:
            # Load and analyze the file
            self.analyzer.load_file(file_path)
            original_code = self.analyzer.original_source

            # Extract code elements
            elements = self.analyzer.extract_code_elements()

            # Apply transformations
            transformed_code = original_code
            all_changes = []

            # Apply naming convention transformations
            if self._has_naming_rules_enabled():
                naming_result = self._apply_naming_transformations(elements)
                if naming_result:
                    transformed_code = naming_result.transformed_code
                    all_changes.extend(naming_result.changes_made)

            # Apply formatting transformations
            if self._has_formatting_rules_enabled():
                formatting_result = self._apply_formatting_transformations(transformed_code)
                if formatting_result:
                    transformed_code = formatting_result
                    all_changes.append("Applied formatting rules")

            return ProcessingResult(
                file_path=file_path,
                success=True,
                original_code=original_code,
                transformed_code=transformed_code,
                changes_made=all_changes,
                error_message=None
            )

        except Exception as e:
            return ProcessingResult(
                file_path=file_path,
                success=False,
                original_code="",
                transformed_code=None,
                changes_made=[],
                error_message=str(e)
            )

    def _has_naming_rules_enabled(self) -> bool:
        """Check if any naming rules are enabled."""
        naming_rules = [
            'variable_naming',
            'function_naming',
            'class_naming',
            'constant_naming',
            'private_method_naming',
            'dunder_method_naming'
        ]
        return any(self.config.is_rule_enabled(rule) for rule in naming_rules)

    def _has_formatting_rules_enabled(self) -> bool:
        """Check if any formatting rules are enabled."""
        # First check the master formatting switch
        formatting_enabled = self.config.get_formatting_rule('enabled')
        if formatting_enabled is False:
            return False

        # If master switch is not explicitly disabled, check individual rules
        formatting_rules = [
            'line_length',
            'operator_spacing',
            'comma_spacing',
            'blank_lines',
            'import_organization'
        ]
        return any(self.config.is_rule_enabled(rule) for rule in formatting_rules)

    def _apply_naming_transformations(self, elements: List[CodeElement]) -> Optional[TransformationResult]:
        """
        Apply naming convention transformations to code elements.

        Args:
            elements: List of code elements to potentially transform

        Returns:
            TransformationResult if any transformations were applied, None otherwise
        """
        transformations = {}
        changes_made = []
        elements_changed = []

        for element in elements:
            new_name = self._get_transformed_name(element)
            if new_name and new_name != element.name:
                transformations[element.name] = new_name
                changes_made.append(f"Renamed {element.element_type} '{element.name}' to '{new_name}'")
                elements_changed.append(element)

        if not transformations:
            return None

        try:
            # Check if formatting is enabled
            formatting_enabled = self.config.get_formatting_rule('enabled')

            if formatting_enabled is False:
                # Use formatting-preserving transformation when formatting is disabled
                print("🎯 Using formatting-preserving transformation (formatting disabled)")
                transformed_code = self.analyzer.apply_transformations_preserve_formatting(transformations)
            else:
                # Use regular AST transformation when formatting is enabled
                print("🎨 Using AST transformation (formatting enabled)")
                transformed_code = self.analyzer.apply_transformations(transformations)

            return TransformationResult(
                original_code=self.analyzer.original_source,
                transformed_code=transformed_code,
                changes_made=changes_made,
                elements_changed=elements_changed
            )
        except Exception as e:
            raise ValueError(f"Error applying naming transformations: {e}")

    def _get_transformed_name(self, element: CodeElement) -> Optional[str]:
        """
        Get the transformed name for a code element based on configuration.

        Args:
            element: CodeElement to transform

        Returns:
            New name if transformation should be applied, None otherwise
        """
        # Map element types to configuration keys
        element_type_mapping = {
            'variable': 'variables',
            'function': 'functions',
            'class': 'classes',
            'constant': 'constants',
            'method': 'functions',  # Regular methods use function naming
            'private_method': 'private_methods',
            'dunder_method': 'dunder_methods'
        }

        # Map element types to rule names
        rule_mapping = {
            'variable': 'variable_naming',
            'function': 'function_naming',
            'class': 'class_naming',
            'constant': 'constant_naming',
            'method': 'function_naming',
            'private_method': 'private_method_naming',
            'dunder_method': 'dunder_method_naming'
        }

        config_key = element_type_mapping.get(element.element_type)
        rule_name = rule_mapping.get(element.element_type)

        if not config_key or not rule_name:
            return None

        if not self.config.is_rule_enabled(rule_name):
            return None

        target_convention = self.config.get_naming_convention(config_key)
        if not target_convention:
            return None

        return self._convert_naming_convention(element.name, target_convention)

    def _convert_naming_convention(self, name: str, target_convention: str) -> str:
        """
        Convert a name to the specified naming convention.

        Args:
            name: Original name
            target_convention: Target naming convention

        Returns:
            Converted name
        """
        if target_convention == "snake_case":
            return self._to_snake_case(name)
        elif target_convention == "camelCase":
            return self._to_camel_case(name)
        elif target_convention == "PascalCase":
            return self._to_pascal_case(name)
        elif target_convention == "UPPER_CASE":
            return self._to_upper_case(name)
        elif target_convention == "_snake_case":
            base_name = self._to_snake_case(name.lstrip('_'))
            return f"_{base_name}"
        elif target_convention == "_camelCase":
            base_name = self._to_camel_case(name.lstrip('_'))
            return f"_{base_name}"
        elif target_convention == "__snake_case__":
            base_name = self._to_snake_case(name.strip('_'))
            return f"__{base_name}__"
        elif target_convention == "__camelCase__":
            base_name = self._to_camel_case(name.strip('_'))
            return f"__{base_name}__"
        else:
            return name

    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        # Handle already snake_case names
        if '_' in name and name.islower():
            return name

        # Convert camelCase and PascalCase to snake_case
        # Insert underscore before uppercase letters that follow lowercase letters
        result = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)

        # Handle sequences of uppercase letters
        result = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', result)

        return result.lower()

    def _to_camel_case(self, name: str) -> str:
        """Convert name to camelCase."""
        if '_' in name:
            # Convert from snake_case
            parts = name.lower().split('_')
            return parts[0] + ''.join(word.capitalize() for word in parts[1:])
        else:
            # Assume it's already in some form of camelCase/PascalCase
            return name[0].lower() + name[1:] if name else name

    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase."""
        if '_' in name:
            # Convert from snake_case
            parts = name.lower().split('_')
            return ''.join(word.capitalize() for word in parts)
        else:
            # Assume it's already in some form of camelCase/PascalCase
            return name[0].upper() + name[1:] if name else name

    def _to_upper_case(self, name: str) -> str:
        """Convert name to UPPER_CASE."""
        if '_' in name:
            return name.upper()
        else:
            # Convert camelCase/PascalCase to UPPER_CASE
            snake_case = self._to_snake_case(name)
            return snake_case.upper()

    def _apply_formatting_transformations(self, source_code: str) -> Optional[str]:
        """
        Apply formatting transformations to source code.

        Args:
            source_code: Source code to format

        Returns:
            Formatted source code if any formatting rules are applied, None otherwise
        """
        # Check master formatting switch first
        formatting_enabled = self.config.get_formatting_rule('enabled')
        if formatting_enabled is False:
            print("🚫 Formatting disabled by master switch - skipping all formatting rules")
            return None

        transformed_code = source_code
        changes_applied = False

        # Apply line length formatting
        if self.config.is_rule_enabled('line_length'):
            max_length = self.config.get_formatting_rule('max_line_length')
            if max_length:
                formatted = self._apply_line_length_formatting(transformed_code, max_length)
                if formatted != transformed_code:
                    transformed_code = formatted
                    changes_applied = True

        # Apply operator spacing
        if self.config.is_rule_enabled('operator_spacing'):
            if self.config.get_formatting_rule('spaces_around_operators'):
                formatted = self._apply_operator_spacing(transformed_code)
                if formatted != transformed_code:
                    transformed_code = formatted
                    changes_applied = True

        # Apply comma spacing
        if self.config.is_rule_enabled('comma_spacing'):
            if self.config.get_formatting_rule('spaces_after_commas'):
                formatted = self._apply_comma_spacing(transformed_code)
                if formatted != transformed_code:
                    transformed_code = formatted
                    changes_applied = True

        # Apply blank lines formatting
        if self.config.is_rule_enabled('blank_lines'):
            formatted = self._apply_blank_lines_formatting(transformed_code)
            if formatted != transformed_code:
                transformed_code = formatted
                changes_applied = True

        return transformed_code if changes_applied else None

    def _apply_line_length_formatting(self, source_code: str, max_length: int) -> str:
        """Apply line length formatting (basic implementation)."""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated line breaking
        lines = source_code.split('\n')
        formatted_lines = []

        for line in lines:
            if len(line) <= max_length:
                formatted_lines.append(line)
            else:
                # Simple line breaking - this could be much more sophisticated
                formatted_lines.append(line)  # For now, keep as-is

        return '\n'.join(formatted_lines)

    def _apply_operator_spacing(self, source_code: str) -> str:
        """Apply operator spacing formatting."""
        # Add spaces around operators (basic implementation)
        patterns = [
            (r'([a-zA-Z0-9_\)])([+\-*/%=<>!&|^]+)([a-zA-Z0-9_\(])', r'\1 \2 \3'),
        ]

        result = source_code
        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)

        return result

    def _apply_comma_spacing(self, source_code: str) -> str:
        """Apply comma spacing formatting."""
        # Add space after commas
        return re.sub(r',([^ \n])', r', \1', source_code)

    def _apply_blank_lines_formatting(self, source_code: str) -> str:
        """Apply blank lines formatting."""
        lines = source_code.split('\n')
        formatted_lines = []

        # This is a simplified implementation
        # You'd want to use AST to properly identify class/function boundaries

        for i, line in enumerate(lines):
            formatted_lines.append(line)

            # Add blank lines after class definitions
            if line.strip().startswith('class ') and line.strip().endswith(':'):
                blank_lines = self.config.get_formatting_rule('blank_lines_after_class') or 2
                for _ in range(blank_lines):
                    formatted_lines.append('')

            # Add blank lines after function definitions
            elif line.strip().startswith('def ') and line.strip().endswith(':'):
                blank_lines = self.config.get_formatting_rule('blank_lines_after_function') or 1
                for _ in range(blank_lines):
                    formatted_lines.append('')

        return '\n'.join(formatted_lines)