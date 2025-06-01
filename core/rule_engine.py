"""
Rule engine for Python Style Converter.
Simplified orchestrator that coordinates naming transformations and formatting.
Enhanced with cross-file symbol tracking and coordinated renaming.
"""

from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
import re

from config.config_manager import ConfigManager
from .ast_analyzer import ASTAnalyzer
from .code_element_extractor import CodeElement
from .code_transformer import TransformationResult
from .global_symbol_tracker import GlobalSymbolMap
from .naming_converter import NamingConverter
from .blank_lines_formatter import BlankLinesFormatter
from .global_transformation_generator import GlobalTransformationGenerator, GlobalTransformation


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
class ProjectProcessingResult:
    """Result of processing an entire project with cross-file coordination."""
    file_results: List[ProcessingResult]
    global_transformations: List[GlobalTransformation]
    cross_file_changes: Dict[Path, List[str]]  # file_path -> list of changes made
    success: bool
    error_message: Optional[str] = None


class RuleEngine:
    """Simplified rule engine that orchestrates transformations."""

    def __init__(self, config_manager: ConfigManager, global_symbol_map: Optional[GlobalSymbolMap] = None):
        """
        Initialize RuleEngine with configuration and optional global context.

        Args:
            config_manager: ConfigManager instance with loaded configuration
            global_symbol_map: Optional global symbol map for cross-file transformations
        """
        self.config = config_manager
        self.global_symbol_map = global_symbol_map

        # Initialize components
        self.analyzer = ASTAnalyzer()
        self.naming_converter = NamingConverter(config_manager)
        self.formatter = BlankLinesFormatter(config_manager)

        # Initialize cross-file components if available
        if global_symbol_map:
            self.global_transformation_generator = GlobalTransformationGenerator(
                config_manager, global_symbol_map
            )
            self.global_transformations: List[GlobalTransformation] = []

    def process_project(self, file_paths: List[Path]) -> ProjectProcessingResult:
        """
        Process an entire project with cross-file coordination.

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
            self.global_transformations = self.global_transformation_generator.generate_global_transformations()

            # Step 2: Process each file with BOTH local and global context
            file_results = []
            cross_file_changes = {}

            for file_path in file_paths:
                print(f"🔄 Processing {file_path} with combined local + cross-file context...")

                # Get cross-file transformations that affect this file
                cross_file_transformations = self.global_transformation_generator.get_transformations_for_file(
                    file_path, self.global_transformations
                )

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

        Args:
            file_path: Path to the Python file to process

        Returns:
            ProcessingResult with transformation results
        """
        if self.global_symbol_map:
            # Use combined context if available
            cross_file_transformations = self.global_transformation_generator.get_transformations_for_file(
                file_path, self.global_transformations
            )
            return self._process_file_with_combined_context(file_path, cross_file_transformations)
        else:
            # Use original single-file processing
            return self._process_file_original(file_path)

    def _process_file_with_combined_context(self, file_path: Path, cross_file_transformations: Dict[str, str]) -> ProcessingResult:
        """
        Process a file with BOTH local and cross-file transformation context.

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

            # Step 1: Apply LOCAL transformations
            local_transformations = {}
            local_changes = []

            if self.naming_converter.is_naming_rules_enabled():
                for element in elements:
                    new_name = self.naming_converter.get_transformed_name(element)
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
                symbol_type = self.global_transformation_generator.get_symbol_type_for_file(old_name, file_path)
                all_changes.append(f"Renamed {symbol_type} '{old_name}' to '{new_name}' (cross-file)")

            if not combined_transformations:
                # Check if we need formatting
                if self.formatter.is_formatting_enabled():
                    formatting_result = self.formatter.apply_blank_lines_formatting(original_code)
                    if formatting_result:
                        return ProcessingResult(
                            file_path=file_path,
                            success=True,
                            original_code=original_code,
                            transformed_code=formatting_result,
                            changes_made=["Applied blank lines formatting"],
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
                # Always use formatting-preserving transformation for naming changes
                transformed_code = self.analyzer.apply_transformations_preserve_formatting(combined_transformations)
                print(f"🎯 Applied {len(combined_transformations)} transformations to {file_path} (formatting preserved)")

            except Exception as e:
                raise ValueError(f"Error applying combined transformations: {e}")

            # Step 5: Apply formatting transformations if enabled
            if self.formatter.is_formatting_enabled():
                formatting_result = self.formatter.apply_blank_lines_formatting(transformed_code)
                if formatting_result:
                    transformed_code = formatting_result
                    all_changes.append("Applied blank lines formatting")

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
        Original single-file processing logic.

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
            if self.naming_converter.is_naming_rules_enabled():
                naming_result = self._apply_naming_transformations(elements)
                if naming_result:
                    transformed_code = naming_result.transformed_code
                    all_changes.extend(naming_result.changes_made)

            # Apply formatting transformations
            if self.formatter.is_formatting_enabled():
                formatting_result = self.formatter.apply_blank_lines_formatting(transformed_code)
                if formatting_result:
                    transformed_code = formatting_result
                    all_changes.append("Applied blank lines formatting")

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
            new_name = self.naming_converter.get_transformed_name(element)
            if new_name and new_name != element.name:
                transformations[element.name] = new_name
                changes_made.append(f"Renamed {element.element_type} '{element.name}' to '{new_name}'")
                elements_changed.append(element)

        if not transformations:
            return None

        try:
            # Always use formatting-preserving transformation for naming changes
            print("🎯 Using formatting-preserving transformation for naming changes")
            transformed_code = self.analyzer.apply_transformations_preserve_formatting(transformations)

            return TransformationResult(
                original_code=self.analyzer.original_source,
                transformed_code=transformed_code,
                changes_made=changes_made,
                elements_changed=elements_changed
            )
        except Exception as e:
            raise ValueError(f"Error applying naming transformations: {e}")