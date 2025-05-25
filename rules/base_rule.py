"""
Base rule class for Python Style Converter.
All transformation rules inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from config.config_manager import ConfigManager
from core.ast_analyzer import CodeElement


@dataclass
class RuleResult:
    """Result of applying a single rule."""
    rule_name: str
    applied: bool
    changes_made: List[str]
    transformations: Dict[str, str]  # old_name -> new_name mapping
    error_message: Optional[str] = None


class BaseRule(ABC):
    """Abstract base class for all transformation rules."""

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the rule with configuration.

        Args:
            config_manager: ConfigManager instance with loaded configuration
        """
        self.config = config_manager
        self.rule_name = self.__class__.__name__.lower().replace('rule', '')

    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if this rule is enabled in the configuration.

        Returns:
            True if rule should be applied, False otherwise
        """
        pass

    @abstractmethod
    def can_apply(self, element: CodeElement) -> bool:
        """
        Check if this rule can be applied to the given code element.

        Args:
            element: CodeElement to check

        Returns:
            True if rule can be applied to this element, False otherwise
        """
        pass

    @abstractmethod
    def apply(self, elements: List[CodeElement]) -> RuleResult:
        """
        Apply this rule to the given code elements.

        Args:
            elements: List of CodeElement objects to process

        Returns:
            RuleResult containing the transformations and changes made
        """
        pass

    def get_rule_description(self) -> str:
        """
        Get a human-readable description of what this rule does.

        Returns:
            Description of the rule's functionality
        """
        return f"{self.__class__.__name__}: No description available"

    def validate_configuration(self) -> List[str]:
        """
        Validate that the configuration is correct for this rule.

        Returns:
            List of validation error messages (empty if valid)
        """
        return []

    def get_priority(self) -> int:
        """
        Get the priority of this rule for execution order.
        Lower numbers execute first.

        Returns:
            Priority number (default is 100)
        """
        return 100