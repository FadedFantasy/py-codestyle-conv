"""
Symbol Definition Data Structures for Python Style Converter.
Contains data classes for representing symbol definitions, usages, and imports.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

from core.code_element_extractor import CodeElement


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