"""
Global Symbol Tracker for Python Style Converter.
Analyzes cross-file symbol definitions and usages for coordinated renaming.
"""

import ast
import os
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

from core.ast_analyzer import CodeElement


@dataclass
class SymbolDefinition:
    """Represents where a symbol is defined."""
    name: str
    symbol_type: str  # 'class', 'function', 'variable', 'constant'
    file_path: Path
    line_number: int
    context: str  # Additional context about the definition
    element: CodeElement  # Reference to the original CodeElement


@dataclass
class SymbolUsage:
    """Represents where a symbol is used."""
    name: str
    usage_type: str  # 'direct', 'import', 'from_import', 'attribute_access'
    file_path: Path
    line_number: int
    context: str  # Context of the usage
    module_context: Optional[str] = None  # For attribute access like 'module.symbol'


@dataclass
class ImportStatement:
    """Represents an import statement."""
    file_path: Path
    line_number: int
    import_type: str  # 'import' or 'from_import'
    module_name: str
    imported_names: List[str]  # List of imported symbols
    aliases: Dict[str, str] = field(default_factory=dict)  # name -> alias mapping


@dataclass
class GlobalSymbolMap:
    """Complete cross-file symbol mapping."""
    definitions: Dict[str, List[SymbolDefinition]] = field(default_factory=lambda: defaultdict(list))
    usages: Dict[str, List[SymbolUsage]] = field(default_factory=lambda: defaultdict(list))
    imports: List[ImportStatement] = field(default_factory=list)
    file_to_module: Dict[Path, str] = field(default_factory=dict)  # file path -> module name
    module_to_file: Dict[str, Path] = field(default_factory=dict)  # module name -> file path


class GlobalSymbolTracker:
    """Tracks symbol definitions and usages across all files in a project."""

    def __init__(self, project_root: Path):
        """
        Initialize the global symbol tracker.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.symbol_map = GlobalSymbolMap()

    def analyze_project(self, file_paths: List[Path]) -> GlobalSymbolMap:
        """
        Analyze all files in the project to build a global symbol map.

        Args:
            file_paths: List of Python files to analyze

        Returns:
            GlobalSymbolMap containing cross-file symbol information
        """
        print(f"🔍 Analyzing {len(file_paths)} files for cross-file symbols...")

        # First pass: Build file-to-module mapping
        self._build_module_mapping(file_paths)

        # Second pass: Extract definitions and imports
        for file_path in file_paths:
            try:
                self._analyze_file_definitions(file_path)
                self._analyze_file_imports(file_path)
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze {file_path}: {e}")
                continue

        # Third pass: Find symbol usages
        for file_path in file_paths:
            try:
                self._analyze_file_usages(file_path)
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze usages in {file_path}: {e}")
                continue

        self._print_analysis_summary()
        return self.symbol_map

    def _build_module_mapping(self, file_paths: List[Path]) -> None:
        """Build mapping between file paths and Python module names."""
        for file_path in file_paths:
            # Convert file path to module name
            relative_path = file_path.relative_to(self.project_root)

            # Remove .py extension and convert path separators to dots
            module_parts = list(relative_path.parts[:-1])  # Remove filename
            filename = relative_path.stem  # Filename without .py

            if filename != '__init__':
                module_parts.append(filename)

            module_name = '.'.join(module_parts) if module_parts else filename

            self.symbol_map.file_to_module[file_path] = module_name
            self.symbol_map.module_to_file[module_name] = file_path

    def _analyze_file_definitions(self, file_path: Path) -> None:
        """Analyze a single file for symbol definitions."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)
        except (FileNotFoundError, UnicodeDecodeError, SyntaxError):
            return

        # Use our existing AST analyzer to extract code elements
        from core.ast_analyzer import ASTAnalyzer
        analyzer = ASTAnalyzer()
        analyzer.load_source(source_code)
        elements = analyzer.extract_code_elements()

        # Convert CodeElements to SymbolDefinitions
        for element in elements:
            symbol_def = SymbolDefinition(
                name=element.name,
                symbol_type=element.element_type,
                file_path=file_path,
                line_number=element.line_number,
                context=element.context,
                element=element
            )
            self.symbol_map.definitions[element.name].append(symbol_def)

    def _analyze_file_imports(self, file_path: Path) -> None:
        """Analyze import statements in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)
        except (FileNotFoundError, UnicodeDecodeError, SyntaxError):
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Handle: import module, import module as alias
                for alias in node.names:
                    import_stmt = ImportStatement(
                        file_path=file_path,
                        line_number=node.lineno,
                        import_type='import',
                        module_name=alias.name,
                        imported_names=[alias.name],
                        aliases={alias.name: alias.asname} if alias.asname else {}
                    )
                    self.symbol_map.imports.append(import_stmt)

            elif isinstance(node, ast.ImportFrom):
                # Handle: from module import symbol, from module import symbol as alias
                if node.module:  # Skip relative imports like "from . import"
                    imported_names = []
                    aliases = {}

                    for alias in node.names:
                        imported_names.append(alias.name)
                        if alias.asname:
                            aliases[alias.name] = alias.asname

                    import_stmt = ImportStatement(
                        file_path=file_path,
                        line_number=node.lineno,
                        import_type='from_import',
                        module_name=node.module,
                        imported_names=imported_names,
                        aliases=aliases
                    )
                    self.symbol_map.imports.append(import_stmt)

    def _analyze_file_usages(self, file_path: Path) -> None:
        """Analyze symbol usages in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)
        except (FileNotFoundError, UnicodeDecodeError, SyntaxError):
            return

        # Build context of imported symbols for this file
        imported_symbols = self._get_imported_symbols_for_file(file_path)

        class UsageVisitor(ast.NodeVisitor):
            def __init__(self, tracker, file_path, imported_symbols):
                self.tracker = tracker
                self.file_path = file_path
                self.imported_symbols = imported_symbols

            def visit_Name(self, node):
                # Direct symbol usage
                if isinstance(node.ctx, ast.Load):  # Symbol is being read/used
                    usage = SymbolUsage(
                        name=node.id,
                        usage_type='direct',
                        file_path=self.file_path,
                        line_number=node.lineno,
                        context='direct_usage'
                    )
                    self.tracker.symbol_map.usages[node.id].append(usage)

                self.generic_visit(node)

            def visit_Attribute(self, node):
                # Handle attribute access like module.symbol
                if isinstance(node.value, ast.Name):
                    # This is module.attribute pattern
                    module_name = node.value.id
                    attribute_name = node.attr

                    usage = SymbolUsage(
                        name=attribute_name,
                        usage_type='attribute_access',
                        file_path=self.file_path,
                        line_number=node.lineno,
                        context=f'attribute_access_on_{module_name}',
                        module_context=module_name
                    )
                    self.tracker.symbol_map.usages[attribute_name].append(usage)

                self.generic_visit(node)

            def visit_Call(self, node):
                # Handle function/class calls
                if isinstance(node.func, ast.Name):
                    # Direct call like MyClass() or my_function()
                    usage = SymbolUsage(
                        name=node.func.id,
                        usage_type='direct',
                        file_path=self.file_path,
                        line_number=node.lineno,
                        context='function_call'
                    )
                    self.tracker.symbol_map.usages[node.func.id].append(usage)
                elif isinstance(node.func, ast.Attribute):
                    # Handle module.function() calls
                    if isinstance(node.func.value, ast.Name):
                        module_name = node.func.value.id
                        function_name = node.func.attr

                        usage = SymbolUsage(
                            name=function_name,
                            usage_type='attribute_access',
                            file_path=self.file_path,
                            line_number=node.lineno,
                            context=f'method_call_on_{module_name}',
                            module_context=module_name
                        )
                        self.tracker.symbol_map.usages[function_name].append(usage)

                self.generic_visit(node)

        visitor = UsageVisitor(self, file_path, imported_symbols)
        visitor.visit(tree)

    def _get_imported_symbols_for_file(self, file_path: Path) -> Dict[str, str]:
        """Get mapping of imported symbols for a specific file."""
        imported_symbols = {}

        for import_stmt in self.symbol_map.imports:
            if import_stmt.file_path == file_path:
                if import_stmt.import_type == 'from_import':
                    # from module import symbol
                    for symbol in import_stmt.imported_names:
                        alias = import_stmt.aliases.get(symbol, symbol)
                        imported_symbols[alias] = f"{import_stmt.module_name}.{symbol}"
                elif import_stmt.import_type == 'import':
                    # import module
                    for module in import_stmt.imported_names:
                        alias = import_stmt.aliases.get(module, module)
                        imported_symbols[alias] = module

        return imported_symbols

    def _print_analysis_summary(self) -> None:
        """Print a summary of the symbol analysis."""
        total_definitions = sum(len(defs) for defs in self.symbol_map.definitions.values())
        total_usages = sum(len(usages) for usages in self.symbol_map.usages.values())

        print(f"📊 Symbol Analysis Summary:")
        print(f"   • Found {total_definitions} symbol definitions")
        print(f"   • Found {total_usages} symbol usages")
        print(f"   • Found {len(self.symbol_map.imports)} import statements")
        print(f"   • Analyzed {len(self.symbol_map.file_to_module)} files")

    def get_cross_file_references(self, symbol_name: str) -> Tuple[List[SymbolDefinition], List[SymbolUsage]]:
        """
        Get all cross-file references for a symbol.

        Args:
            symbol_name: Name of the symbol to analyze

        Returns:
            Tuple of (definitions, usages) across all files
        """
        definitions = self.symbol_map.definitions.get(symbol_name, [])
        usages = self.symbol_map.usages.get(symbol_name, [])

        return definitions, usages

    def get_symbols_to_rename(self, old_name: str, new_name: str) -> Dict[Path, List[Tuple[int, str, str]]]:
        """
        Get all locations where a symbol needs to be renamed.

        Args:
            old_name: Current symbol name
            new_name: New symbol name

        Returns:
            Dictionary mapping file paths to list of (line_number, old_text, new_text) tuples
        """
        rename_locations = defaultdict(list)

        # Add definitions
        for definition in self.symbol_map.definitions.get(old_name, []):
            rename_locations[definition.file_path].append((
                definition.line_number,
                old_name,
                new_name
            ))

        # Add usages
        for usage in self.symbol_map.usages.get(old_name, []):
            rename_locations[usage.file_path].append((
                usage.line_number,
                old_name,
                new_name
            ))

        return dict(rename_locations)