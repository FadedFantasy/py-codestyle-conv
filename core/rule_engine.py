"""
Rule engine for Python Style Converter.
Orchestrates all code transformations based on configuration.
Enhanced with cross-file symbol tracking and coordinated renaming.
Fixed to combine both local and cross-file transformations.
"""

from typing import Dict, List, Tuple, Optional, Any, Set
from pathlib import Path
from dataclasses import dataclass
import re

from config.config_manager import ConfigManager
from .ast_analyzer import ASTAnalyzer, CodeElement, TransformationResult
from .global_symbol_tracker import GlobalSymbolTracker, GlobalSymbolMap, SymbolDefinition


@dataclass
class ProcessingResult:
    """Result of processing a single file."""
    file_path: Path
    success: bool
    original_code: str
    transformed_code: Optional[str]
    changes_made: List[str]
    error_message: Optional[str]


@dataclass
class GlobalTransformation:
    """Represents a transformation that affects multiple files."""
    old_name: str
    new_name: str
    symbol_type: str  # 'class', 'function', 'variable', 'constant'
    definition_file: Path
    affected_files: List[Path]
    transformation_type: str  # 'naming_convention', 'formatting', etc.


@dataclass
class ProjectProcessingResult:
    """Result of processing an entire project with cross-file coordination."""
    file_results: List[ProcessingResult]
    global_transformations: List[GlobalTransformation]
    cross_file_changes: Dict[Path, List[str]]  # file_path -> list of changes made
    success: bool
    error_message: Optional[str] = None


class RuleEngine:
    """Main engine that applies all transformation rules to Python code."""

    def __init__(self, config_manager: ConfigManager, global_symbol_map: Optional[GlobalSymbolMap] = None):
        """
        Initialize RuleEngine with configuration and optional global context.

        Args:
            config_manager: ConfigManager instance with loaded configuration
            global_symbol_map: Optional global symbol map for cross-file transformations
        """
        self.config = config_manager
        self.analyzer = ASTAnalyzer()
        self.global_symbol_map = global_symbol_map
        self.global_transformations: List[GlobalTransformation] = []

    def process_project(self, file_paths: List[Path]) -> ProjectProcessingResult:
        """
        Process an entire project with cross-file coordination.
        This is the new main entry point for cross-file transformations.

        Args:
            file_paths: List of Python files to process

        Returns:
            ProjectProcessingResult with coordinated transformations
        """
        if not self.global_symbol_map:
            # Fallback to individual file processing if no global context
            print("⚠️  No global symbol map provided, falling back to individual file processing")
            return self._process_files_individually(file_paths)

        try:
            print(f"🌐 Processing {len(file_paths)} files with cross-file coordination...")

            # Step 1: Generate global transformations plan
            self.global_transformations = self._generate_global_transformations()

            # Step 2: Process each file with BOTH local and global context
            file_results = []
            cross_file_changes = {}

            for file_path in file_paths:
                print(f"🔄 Processing {file_path} with combined local + cross-file context...")

                # Get cross-file transformations that affect this file
                cross_file_transformations = self._get_transformations_for_file(file_path)

                # Process the file with BOTH local and cross-file transformations
                result = self._process_file_with_combined_context(file_path, cross_file_transformations)
                file_results.append(result)

                # Track cross-file changes
                if result.success and result.changes_made:
                    cross_file_changes[file_path] = result.changes_made

            success = all(result.success for result in file_results)

            return ProjectProcessingResult(
                file_results=file_results,
                global_transformations=self.global_transformations,
                cross_file_changes=cross_file_changes,
                success=success
            )

        except Exception as e:
            return ProjectProcessingResult(
                file_results=[],
                global_transformations=[],
                cross_file_changes={},
                success=False,
                error_message=f"Error in project processing: {e}"
            )

    def process_file(self, file_path: Path) -> ProcessingResult:
        """
        Process a single Python file according to configuration.
        This maintains backward compatibility with the original API.

        Args:
            file_path: Path to the Python file to process

        Returns:
            ProcessingResult with transformation results
        """
        if self.global_symbol_map:
            # Use combined context if available
            cross_file_transformations = self._get_transformations_for_file(file_path)
            return self._process_file_with_combined_context(file_path, cross_file_transformations)
        else:
            # Use original single-file processing
            return self._process_file_original(file_path)

    def _generate_global_transformations(self) -> List[GlobalTransformation]:
        """
        Generate global transformations by analyzing all symbol definitions
        and determining which ones need to be renamed according to configuration.

        Returns:
            List of GlobalTransformation objects
        """
        transformations = []

        print("🔍 Analyzing symbols for global transformations...")

        # Process each unique symbol defined in the project
        for symbol_name, definitions in self.global_symbol_map.definitions.items():
            if not definitions:
                continue

            # Get the primary definition (first one, or one in main module)
            primary_def = self._get_primary_definition(definitions)
            if not primary_def:
                continue

            # Check if this symbol should be transformed
            new_name = self._get_transformed_name(primary_def.element)
            if new_name and new_name != symbol_name:
                # Find all files affected by this transformation
                affected_files = self._get_affected_files(symbol_name)

                transformation = GlobalTransformation(
                    old_name=symbol_name,
                    new_name=new_name,
                    symbol_type=primary_def.symbol_type,
                    definition_file=primary_def.file_path,
                    affected_files=affected_files,
                    transformation_type='naming_convention'
                )
                transformations.append(transformation)

                print(f"🎯 Global transformation: {symbol_name} → {new_name} (affects {len(affected_files)} files)")

        print(f"✅ Generated {len(transformations)} global transformations")
        return transformations

    def _get_primary_definition(self, definitions: List[SymbolDefinition]) -> Optional[SymbolDefinition]:
        """
        Get the primary definition for a symbol when there are multiple definitions.

        Args:
            definitions: List of symbol definitions

        Returns:
            Primary definition to use for transformation decisions
        """
        if len(definitions) == 1:
            return definitions[0]

        # If multiple definitions, prefer:
        # 1. Non-test files over test files
        # 2. Files closer to project root
        # 3. First definition found

        non_test_defs = [d for d in definitions if 'test' not in str(d.file_path).lower()]
        if non_test_defs:
            return sorted(non_test_defs, key=lambda d: len(d.file_path.parts))[0]

        return definitions[0]

    def _get_affected_files(self, symbol_name: str) -> List[Path]:
        """
        Get all files that are affected by renaming a symbol.

        Args:
            symbol_name: Name of the symbol being renamed

        Returns:
            List of file paths that contain references to this symbol
        """
        affected_files = set()

        # Add files where symbol is defined
        for definition in self.global_symbol_map.definitions.get(symbol_name, []):
            affected_files.add(definition.file_path)

        # Add files where symbol is used
        for usage in self.global_symbol_map.usages.get(symbol_name, []):
            affected_files.add(usage.file_path)

        # Add files that import this symbol
        for import_stmt in self.global_symbol_map.imports:
            if symbol_name in import_stmt.imported_names:
                affected_files.add(import_stmt.file_path)

        return list(affected_files)

    def _get_transformations_for_file(self, file_path: Path) -> Dict[str, str]:
        """
        Get cross-file transformations that affect a specific file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary mapping old names to new names for this file
        """
        transformations = {}

        for global_transform in self.global_transformations:
            if file_path in global_transform.affected_files:
                transformations[global_transform.old_name] = global_transform.new_name

        return transformations

    def _process_file_with_combined_context(self, file_path: Path, cross_file_transformations: Dict[str, str]) -> ProcessingResult:
        """
        Process a file with BOTH local and cross-file transformation context.
        This combines the original functionality with cross-file capabilities.

        Args:
            file_path: Path to the file to process
            cross_file_transformations: Cross-file transformations to apply to this file

        Returns:
            ProcessingResult for this file
        """
        try:
            # Load and analyze the file
            self.analyzer.load_file(file_path)
            original_code = self.analyzer.original_source

            # Extract code elements for local transformations
            elements = self.analyzer.extract_code_elements()

            # Step 1: Apply LOCAL transformations (original functionality)
            local_transformations = {}
            local_changes = []

            if self._has_naming_rules_enabled():
                for element in elements:
                    new_name = self._get_transformed_name(element)
                    if new_name and new_name != element.name:
                        local_transformations[element.name] = new_name
                        local_changes.append(f"Renamed {element.element_type} '{element.name}' to '{new_name}'")

            # Step 2: Combine local and cross-file transformations
            # Cross-file transformations override local ones if there's a conflict
            combined_transformations = {**local_transformations, **cross_file_transformations}

            # Step 3: Generate combined change descriptions
            all_changes = []

            # Add local changes (that aren't overridden by cross-file)
            for change in local_changes:
                # Extract the old name from the change description
                match = re.search(r"'([^']+)' to '([^']+)'", change)
                if match:
                    old_name = match.group(1)
                    # Only add if this wasn't overridden by cross-file transformation
                    if old_name not in cross_file_transformations:
                        all_changes.append(change)

            # Add cross-file changes
            for old_name, new_name in cross_file_transformations.items():
                # Determine what type of symbol this is
                symbol_type = self._get_symbol_type_for_file(old_name, file_path)
                all_changes.append(f"Renamed {symbol_type} '{old_name}' to '{new_name}' (cross-file)")

            if not combined_transformations:
                # Check if we need formatting
                if self._has_formatting_rules_enabled():
                    formatting_result = self._apply_formatting_transformations(original_code)
                    if formatting_result:
                        return ProcessingResult(
                            file_path=file_path,
                            success=True,
                            original_code=original_code,
                            transformed_code=formatting_result,
                            changes_made=["Applied formatting rules"],
                            error_message=None
                        )

                # No transformations needed for this file
                return ProcessingResult(
                    file_path=file_path,
                    success=True,
                    original_code=original_code,
                    transformed_code=original_code,
                    changes_made=[],
                    error_message=None
                )

            # Step 4: Apply combined transformations
            try:
                # Check if formatting is enabled
                formatting_enabled = self.config.get_formatting_rule('enabled')

                if formatting_enabled is False:
                    # Use formatting-preserving transformation
                    transformed_code = self.analyzer.apply_transformations_preserve_formatting(combined_transformations)
                    print(f"🎯 Applied {len(combined_transformations)} transformations to {file_path} (formatting preserved)")
                else:
                    # Use regular AST transformation
                    transformed_code = self.analyzer.apply_transformations(combined_transformations)
                    print(f"🎨 Applied {len(combined_transformations)} transformations to {file_path} (AST mode)")

            except Exception as e:
                raise ValueError(f"Error applying combined transformations: {e}")

            # Step 5: Apply formatting transformations if enabled
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

    def _get_symbol_type_for_file(self, symbol_name: str, file_path: Path) -> str:
        """Get the symbol type for a symbol in a specific file."""
        # Check definitions in this file
        for definition in self.global_symbol_map.definitions.get(symbol_name, []):
            if definition.file_path == file_path:
                return definition.symbol_type

        # Check usages to infer type
        for usage in self.global_symbol_map.usages.get(symbol_name, []):
            if usage.file_path == file_path:
                if 'class' in usage.context.lower():
                    return 'class'
                elif 'function' in usage.context.lower():
                    return 'function'

        return 'symbol'  # Generic fallback

    def _process_files_individually(self, file_paths: List[Path]) -> ProjectProcessingResult:
        """
        Fallback: Process files individually without global coordination.

        Args:
            file_paths: List of files to process

        Returns:
            ProjectProcessingResult with individual file results
        """
        file_results = []

        for file_path in file_paths:
            result = self._process_file_original(file_path)
            file_results.append(result)

        success = all(result.success for result in file_results)

        return ProjectProcessingResult(
            file_results=file_results,
            global_transformations=[],
            cross_file_changes={},
            success=success
        )

    def _process_file_original(self, file_path: Path) -> ProcessingResult:
        """
        Original single-file processing logic (unchanged for backward compatibility).

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

    # ==========================================
    # Original methods (unchanged for compatibility)
    # ==========================================

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