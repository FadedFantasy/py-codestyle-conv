"""
Cross-File Transformer for Python Style Converter.
Handles coordinated transformations across multiple files including import statement updates.
"""

import ast
import re
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

from .global_symbol_tracker import GlobalSymbolMap, ImportStatement
from .rule_engine import GlobalTransformation


@dataclass
class FileTransformation:
    """Represents all transformations to be applied to a single file."""
    file_path: Path
    original_content: str
    transformed_content: str
    transformations_applied: Dict[str, str]  # old_name -> new_name
    import_updates: List[str]  # Description of import updates made
    changes_made: List[str]  # Human-readable list of changes


@dataclass
class CrossFileTransformationResult:
    """Result of applying cross-file transformations."""
    file_transformations: Dict[Path, FileTransformation]
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CrossFileTransformer:
    """Handles coordinated transformations across multiple files."""

    def __init__(self, global_symbol_map: GlobalSymbolMap):
        """
        Initialize the cross-file transformer.

        Args:
            global_symbol_map: Global symbol map with cross-file relationships
        """
        self.global_symbol_map = global_symbol_map
        self.file_contents: Dict[Path, str] = {}

    def apply_global_transformations(self,
                                   global_transformations: List[GlobalTransformation],
                                   preserve_formatting: bool = True) -> CrossFileTransformationResult:
        """
        Apply global transformations across all affected files.

        Args:
            global_transformations: List of coordinated transformations to apply
            preserve_formatting: Whether to preserve original formatting

        Returns:
            CrossFileTransformationResult with all file changes
        """
        print(f"🌐 Applying {len(global_transformations)} global transformations...")

        try:
            # Step 1: Load all affected files
            affected_files = self._get_all_affected_files(global_transformations)
            self._load_file_contents(affected_files)

            # Step 2: Apply transformations to each file
            file_transformations = {}
            errors = []
            warnings = []

            for file_path in affected_files:
                try:
                    # Get transformations that affect this file
                    file_specific_transformations = self._get_transformations_for_file(
                        file_path, global_transformations
                    )

                    if file_specific_transformations:
                        # Apply transformations to this file
                        file_result = self._transform_single_file(
                            file_path,
                            file_specific_transformations,
                            preserve_formatting
                        )
                        file_transformations[file_path] = file_result

                        print(f"✅ Transformed {file_path}: {len(file_result.changes_made)} changes")
                    else:
                        print(f"⏩ Skipped {file_path}: no transformations needed")

                except Exception as e:
                    error_msg = f"Error transforming {file_path}: {e}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")

            success = len(errors) == 0

            return CrossFileTransformationResult(
                file_transformations=file_transformations,
                success=success,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            return CrossFileTransformationResult(
                file_transformations={},
                success=False,
                errors=[f"Critical error in cross-file transformation: {e}"]
            )

    def _get_all_affected_files(self, global_transformations: List[GlobalTransformation]) -> Set[Path]:
        """Get all files that will be affected by the global transformations."""
        affected_files = set()

        for transformation in global_transformations:
            affected_files.update(transformation.affected_files)

        return affected_files

    def _load_file_contents(self, file_paths: Set[Path]) -> None:
        """Load content of all files that need to be transformed."""
        print(f"📂 Loading {len(file_paths)} files...")

        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.file_contents[file_path] = f.read()
            except Exception as e:
                print(f"⚠️  Warning: Could not load {file_path}: {e}")

    def _get_transformations_for_file(self,
                                    file_path: Path,
                                    global_transformations: List[GlobalTransformation]) -> Dict[str, str]:
        """Get all transformations that affect a specific file."""
        transformations = {}

        for global_transform in global_transformations:
            if file_path in global_transform.affected_files:
                transformations[global_transform.old_name] = global_transform.new_name

        return transformations

    def _transform_single_file(self,
                             file_path: Path,
                             transformations: Dict[str, str],
                             preserve_formatting: bool) -> FileTransformation:
        """
        Apply transformations to a single file.

        Args:
            file_path: Path to the file to transform
            transformations: Dictionary of old_name -> new_name mappings
            preserve_formatting: Whether to preserve formatting

        Returns:
            FileTransformation with the results
        """
        original_content = self.file_contents[file_path]
        transformed_content = original_content
        changes_made = []
        import_updates = []

        try:
            # Step 1: Update import statements
            updated_content, import_changes = self._update_import_statements(
                transformed_content, file_path, transformations
            )
            transformed_content = updated_content
            import_updates.extend(import_changes)

            # Step 2: Update symbol usages in code
            updated_content, symbol_changes = self._update_symbol_usages(
                transformed_content, transformations, preserve_formatting
            )
            transformed_content = updated_content
            changes_made.extend(symbol_changes)

            # Step 3: Update symbol definitions (classes, functions, etc.)
            updated_content, definition_changes = self._update_symbol_definitions(
                transformed_content, transformations, preserve_formatting
            )
            transformed_content = updated_content
            changes_made.extend(definition_changes)

            # Combine all changes
            all_changes = changes_made + import_updates

            return FileTransformation(
                file_path=file_path,
                original_content=original_content,
                transformed_content=transformed_content,
                transformations_applied=transformations,
                import_updates=import_updates,
                changes_made=all_changes
            )

        except Exception as e:
            raise ValueError(f"Error transforming file {file_path}: {e}")

    def _update_import_statements(self,
                                content: str,
                                file_path: Path,
                                transformations: Dict[str, str]) -> Tuple[str, List[str]]:
        """
        Update import statements to reflect renamed symbols.

        Args:
            content: File content
            file_path: Path to the file being processed
            transformations: Symbol name mappings

        Returns:
            Tuple of (updated_content, list_of_changes_made)
        """
        updated_content = content
        changes_made = []

        try:
            # Parse the file to find import statements
            tree = ast.parse(content)
        except SyntaxError:
            # If we can't parse, try regex-based approach
            return self._update_imports_with_regex(content, transformations)

        # Track line-by-line changes for reconstruction
        lines = content.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Handle: from module import symbol
                if node.module and hasattr(node, 'names'):
                    for alias in node.names:
                        if alias.name in transformations:
                            old_name = alias.name
                            new_name = transformations[old_name]

                            # Update the specific line
                            line_idx = node.lineno - 1  # Convert to 0-based index
                            if line_idx < len(lines):
                                old_line = lines[line_idx]

                                # Replace the import name, being careful about aliases
                                if alias.asname:
                                    # Handle: from module import old_name as alias
                                    pattern = rf'\b{re.escape(old_name)}\s+as\s+{re.escape(alias.asname)}\b'
                                    replacement = f'{new_name} as {alias.asname}'
                                else:
                                    # Handle: from module import old_name
                                    pattern = rf'\b{re.escape(old_name)}\b'
                                    replacement = new_name

                                new_line = re.sub(pattern, replacement, old_line)
                                if new_line != old_line:
                                    lines[line_idx] = new_line
                                    changes_made.append(f"Updated import: {old_name} → {new_name}")

            elif isinstance(node, ast.Import):
                # Handle: import module (where module might be renamed)
                # This is less common for our use case, but handle it for completeness
                for alias in node.names:
                    if alias.name in transformations:
                        old_name = alias.name
                        new_name = transformations[old_name]

                        line_idx = node.lineno - 1
                        if line_idx < len(lines):
                            old_line = lines[line_idx]

                            if alias.asname:
                                # Handle: import old_module as alias
                                pattern = rf'\b{re.escape(old_name)}\s+as\s+{re.escape(alias.asname)}\b'
                                replacement = f'{new_name} as {alias.asname}'
                            else:
                                # Handle: import old_module
                                pattern = rf'\b{re.escape(old_name)}\b'
                                replacement = new_name

                            new_line = re.sub(pattern, replacement, old_line)
                            if new_line != old_line:
                                lines[line_idx] = new_line
                                changes_made.append(f"Updated module import: {old_name} → {new_name}")

        updated_content = '\n'.join(lines)
        return updated_content, changes_made

    def _update_imports_with_regex(self,
                                 content: str,
                                 transformations: Dict[str, str]) -> Tuple[str, List[str]]:
        """
        Fallback regex-based import updating when AST parsing fails.

        Args:
            content: File content
            transformations: Symbol name mappings

        Returns:
            Tuple of (updated_content, list_of_changes_made)
        """
        updated_content = content
        changes_made = []

        for old_name, new_name in transformations.items():
            # Pattern for: from module import old_name
            from_import_pattern = rf'(\bfrom\s+\w+(?:\.\w+)*\s+import\s+.*?\b)({re.escape(old_name)})(\b)'
            matches = re.finditer(from_import_pattern, updated_content)

            for match in matches:
                old_full = match.group(0)
                new_full = old_full.replace(old_name, new_name)
                updated_content = updated_content.replace(old_full, new_full)
                changes_made.append(f"Updated import (regex): {old_name} → {new_name}")

        return updated_content, changes_made

    def _update_symbol_usages(self,
                            content: str,
                            transformations: Dict[str, str],
                            preserve_formatting: bool) -> Tuple[str, List[str]]:
        """
        Update symbol usages in the code (not definitions).

        Args:
            content: File content
            transformations: Symbol name mappings
            preserve_formatting: Whether to preserve formatting

        Returns:
            Tuple of (updated_content, list_of_changes_made)
        """
        updated_content = content
        changes_made = []

        # Sort transformations by length (longer first) to avoid partial replacements
        sorted_transformations = sorted(transformations.items(), key=lambda x: len(x[0]), reverse=True)

        for old_name, new_name in sorted_transformations:
            # Count occurrences before replacement
            old_count = len(re.findall(rf'\b{re.escape(old_name)}\b', updated_content))

            if old_count > 0:
                # Replace symbol usages (not in strings or comments)
                patterns_to_try = [
                    # Direct usage: old_name()
                    (rf'\b{re.escape(old_name)}\b(?=\s*\()', f'{new_name}'),
                    # Attribute access: obj.old_name
                    (rf'(\.)({re.escape(old_name)})\b', rf'\1{new_name}'),
                    # Variable assignment: old_name =
                    (rf'\b{re.escape(old_name)}\b(?=\s*=)', f'{new_name}'),
                    # General usage: old_name (as word boundary)
                    (rf'\b{re.escape(old_name)}\b', f'{new_name}')
                ]

                content_before = updated_content
                for pattern, replacement in patterns_to_try:
                    updated_content = re.sub(pattern, replacement, updated_content)

                # Count changes made
                if updated_content != content_before:
                    new_count = len(re.findall(rf'\b{re.escape(new_name)}\b', updated_content))
                    changes_count = new_count - (old_count - len(re.findall(rf'\b{re.escape(old_name)}\b', updated_content)))
                    if changes_count > 0:
                        changes_made.append(f"Updated {changes_count} usage(s) of '{old_name}' to '{new_name}'")

        return updated_content, changes_made

    def _update_symbol_definitions(self,
                                 content: str,
                                 transformations: Dict[str, str],
                                 preserve_formatting: bool) -> Tuple[str, List[str]]:
        """
        Update symbol definitions (class, function, variable definitions).

        Args:
            content: File content
            transformations: Symbol name mappings
            preserve_formatting: Whether to preserve formatting

        Returns:
            Tuple of (updated_content, list_of_changes_made)
        """
        updated_content = content
        changes_made = []

        for old_name, new_name in transformations.items():
            # Patterns for different types of definitions
            definition_patterns = [
                # Class definitions: class OldName:
                (rf'(\bclass\s+){re.escape(old_name)}(\s*\([^)]*\)?)', rf'\1{new_name}\2', 'class'),
                # Function definitions: def old_name(
                (rf'(\bdef\s+){re.escape(old_name)}(\s*\()', rf'\1{new_name}\2', 'function'),
                # Async function definitions: async def old_name(
                (rf'(\basync\s+def\s+){re.escape(old_name)}(\s*\()', rf'\1{new_name}\2', 'async function'),
                # Variable definitions: old_name = (at start of line or after whitespace)
                (rf'(^|\s+)({re.escape(old_name)})(\s*=)', rf'\1{new_name}\3', 'variable'),
            ]

            for pattern, replacement, def_type in definition_patterns:
                matches = re.finditer(pattern, updated_content, re.MULTILINE)
                match_count = len(list(re.finditer(pattern, updated_content, re.MULTILINE)))

                if match_count > 0:
                    updated_content = re.sub(pattern, replacement, updated_content, flags=re.MULTILINE)
                    changes_made.append(f"Updated {def_type} definition: '{old_name}' → '{new_name}'")

        return updated_content, changes_made

    def validate_transformations(self, result: CrossFileTransformationResult) -> List[str]:
        """
        Validate that the transformations don't break the code.

        Args:
            result: Cross-file transformation result to validate

        Returns:
            List of validation errors (empty if all good)
        """
        validation_errors = []

        for file_path, transformation in result.file_transformations.items():
            try:
                # Try to parse the transformed code
                ast.parse(transformation.transformed_content)
            except SyntaxError as e:
                validation_errors.append(
                    f"Syntax error in transformed {file_path}: {e}"
                )

        return validation_errors

    def get_transformation_summary(self, result: CrossFileTransformationResult) -> Dict[str, Any]:
        """
        Get a summary of all transformations applied.

        Args:
            result: Cross-file transformation result

        Returns:
            Summary dictionary with statistics and details
        """
        total_files = len(result.file_transformations)
        total_changes = sum(len(ft.changes_made) for ft in result.file_transformations.values())
        total_import_updates = sum(len(ft.import_updates) for ft in result.file_transformations.values())

        # Count transformations by type
        transformation_counts = defaultdict(int)
        for transformation in result.file_transformations.values():
            for change in transformation.changes_made:
                if 'class' in change.lower():
                    transformation_counts['classes'] += 1
                elif 'function' in change.lower():
                    transformation_counts['functions'] += 1
                elif 'variable' in change.lower():
                    transformation_counts['variables'] += 1
                elif 'usage' in change.lower():
                    transformation_counts['usages'] += 1

        return {
            'total_files_modified': total_files,
            'total_changes': total_changes,
            'total_import_updates': total_import_updates,
            'transformation_counts': dict(transformation_counts),
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings
        }