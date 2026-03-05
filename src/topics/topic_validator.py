"""Topic validation for schema and format checking."""

import re
from typing import Any, Dict, List, Optional

from src.topics.config import TopicsConfig


class TopicValidationError(Exception):
    """Exception for topic validation errors."""

    pass


class TopicValidator:
    """Validator for topic extraction results."""

    def __init__(self, config: TopicsConfig = None):
        self.config = config or TopicsConfig()

    def validate_topics(self, topics: List[Dict[str, Any]]) -> bool:
        """Validate topics list format.

        Args:
            topics: List of topic dictionaries

        Returns:
            True if valid, raises TopicValidationError otherwise
        """
        # Check number of topics
        if len(topics) != self.config.topics_per_note:
            raise TopicValidationError(
                f"Expected {self.config.topics_per_note} topics, got {len(topics)}"
            )

        seen_names = set()

        for i, topic in enumerate(topics):
            # Required fields
            required_fields = {"name", "weight", "confidence"}
            missing = required_fields - set(topic.keys())
            if missing:
                raise TopicValidationError(f"Topic {i}: Missing fields: {missing}")

            # Validate name
            name = topic["name"]
            if not isinstance(name, str):
                raise TopicValidationError(f"Topic {i}: name must be string")

            if not name:
                raise TopicValidationError(f"Topic {i}: name cannot be empty")

            # Check for snake_case
            if not re.match(r"^[a-z][a-z0-9_]*$", name):
                raise TopicValidationError(
                    f"Topic {i}: name '{name}' must be snake_case"
                )

            # Check for duplicates
            if name in seen_names:
                raise TopicValidationError(f"Topic {i}: Duplicate name '{name}'")
            seen_names.add(name)

            # Validate weight
            weight = topic["weight"]
            if not isinstance(weight, int):
                raise TopicValidationError(f"Topic {i}: weight must be integer")

            if not (self.config.weight_min <= weight <= self.config.weight_max):
                raise TopicValidationError(
                    f"Topic {i}: weight {weight} not in range "
                    f"[{self.config.weight_min}, {self.config.weight_max}]"
                )

            # Validate confidence
            confidence = topic["confidence"]
            if not isinstance(confidence, (int, float)):
                raise TopicValidationError(f"Topic {i}: confidence must be number")

            if not (0.0 <= confidence <= 1.0):
                raise TopicValidationError(
                    f"Topic {i}: confidence {confidence} not in range [0.0, 1.0]"
                )

        return True

    def validate_cdu(
        self, cdu_primary: Optional[str], cdu_secondary: Optional[List[str]]
    ) -> bool:
        """Validate CDU classification.

        Args:
            cdu_primary: Primary CDU code
            cdu_secondary: List of secondary CDU codes

        Returns:
            True if valid, raises TopicValidationError otherwise
        """
        from src.topics.taxonomy_manager import CDUManager

        # Primary CDU is optional (can be null)
        if cdu_primary is not None:
            # Try to normalize first
            normalized = CDUManager.normalize_cdu(cdu_primary)
            if normalized:
                cdu_primary = normalized
            elif not CDUManager.validate_cdu_format(cdu_primary):
                raise TopicValidationError(f"Invalid CDU primary format: {cdu_primary}")

        # Secondary CDUs
        if cdu_secondary is not None:
            if not isinstance(cdu_secondary, list):
                raise TopicValidationError("cdu_secondary must be a list")

            for cdu in cdu_secondary:
                # Try to normalize first
                normalized = CDUManager.normalize_cdu(cdu)
                if normalized:
                    cdu = normalized
                elif not CDUManager.validate_cdu_format(cdu):
                    raise TopicValidationError(f"Invalid CDU secondary format: {cdu}")

        return True

    def validate_full_result(self, result: Dict[str, Any]) -> bool:
        """Validate full extraction result.

        Args:
            result: Dictionary with topics, cdu_primary, cdu_secondary

        Returns:
            True if valid, raises TopicValidationError otherwise
        """
        # Check topics
        if "topics" not in result:
            raise TopicValidationError("Missing 'topics' field")

        if not isinstance(result["topics"], list):
            raise TopicValidationError("'topics' must be a list")

        self.validate_topics(result["topics"])

        # CDU fields
        cdu_primary = result.get("cdu_primary")
        cdu_secondary = result.get("cdu_secondary")

        self.validate_cdu(cdu_primary, cdu_secondary)

        return True
