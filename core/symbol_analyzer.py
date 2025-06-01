"""
Symbol Analyzer for Python Style Converter.
Analyzes individual files for symbol definitions, usages, and imports.
"""

import ast
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path

from .symbol_definitions import SymbolDefinition, SymbolUsage, ImportStatement
from .ast_analyzer import ASTAnalyzer


class SymbolAnalyzer:
    """Analyzes individual files for symbols."""

    def __init__(self):
        """Initialize the symbol analyzer."""
        self.analyzer = ASTAnalyzer()

    def analyze_file_definitions(self, file_path: Path) -> List[SymbolDefinition]:
        """
        Analyze a single file for symbol definitions.

        Args:
            file_path: Path to the file to analyze

        Returns:
            List of SymbolDefinition objects
        """
        try:
            self.analyzer.load_file(file_path)
            elements = self.analyzer.extract_code_elements()

            # Convert CodeElements to SymbolDefinitions
            definitions = []
            for element in elements:
                symbol_def = SymbolDefinition(
                    name=element.name,
                    symbol_type=element.element_type,
                    file_path=file_path,
                    line_number=element.line_number,
                    context=element.context,
                    element=element
                )
                definitions.append(symbol_def)

            return definitions

        except (FileNotFoundError, UnicodeDecodeError, SyntaxError):
            return []

    def analyze_file_imports(self, file_path: Path) -> List[ImportStatement]:
        """
        Analyze import statements in a file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            List of ImportStatement objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)
        except (FileNotFoundError, UnicodeDecodeError, SyntaxError):
            return []

        imports = []

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
                    imports.append(import_stmt)

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
                    imports.append(import_stmt)

        return imports

    def analyze_file_usages(self, file_path: Path, imported_symbols: Dict[str, str]) -> List[SymbolUsage]:
        """
        Analyze symbol usages in a file.

        Args:
            file_path: Path to the file to analyze
            imported_symbols: Dictionary of imported symbols for this file

        Returns:
            List of SymbolUsage objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)
        except (FileNotFoundError, UnicodeDecodeError, SyntaxError):
            return []

        usages = []

        class UsageVisitor(ast.NodeVisitor):
            def __init__(self, analyzer, file_path, imported_symbols):
                self.analyzer = analyzer
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
                    usages.append(usage)

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
                    usages.append(usage)

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
                    usages.append(usage)
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
                        usages.append(usage)

                self.generic_visit(node)

        visitor = UsageVisitor(self, file_path, imported_symbols)
        visitor.visit(tree)

        return usages

    def get_imported_symbols_for_file(self, file_path: Path, all_imports: List[ImportStatement]) -> Dict[str, str]:
        """
        Get mapping of imported symbols for a specific file.

        Args:
            file_path: Path to the file
            all_imports: All import statements in the project

        Returns:
            Dictionary mapping symbol names to their full module paths
        """
        imported_symbols = {}

        for import_stmt in all_imports:
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