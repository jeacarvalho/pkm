"""Topic validation for schema and format checking."""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from src.topics.config import TopicConfig


def remove_accents(text: str) -> str:
    """Remove accents from text while preserving base characters.

    Also transliterates Cyrillic and Arabic characters to their Latin equivalents.

    Args:
        text: Input text with possible accents

    Returns:
        Text without accents
    """
    # Normalize to NFD (decomposed form), then remove combining characters
    normalized = unicodedata.normalize("NFD", text)
    # Filter out combining characters (Mn category)
    result = "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    # Transliterate Cyrillic characters to Latin
    cyrillic_to_latin = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
        "А": "A",
        "Б": "B",
        "В": "V",
        "Г": "G",
        "Д": "D",
        "Е": "E",
        "Ё": "E",
        "Ж": "Zh",
        "З": "Z",
        "И": "I",
        "Й": "Y",
        "К": "K",
        "Л": "L",
        "М": "M",
        "Н": "N",
        "О": "O",
        "П": "P",
        "Р": "R",
        "С": "S",
        "Т": "T",
        "У": "U",
        "Ф": "F",
        "Х": "H",
        "Ц": "Ts",
        "Ч": "Ch",
        "Ш": "Sh",
        "Щ": "Sch",
        "Ъ": "",
        "Ы": "Y",
        "Ь": "",
        "Э": "E",
        "Ю": "Yu",
        "Я": "Ya",
    }

    # Transliterate Arabic characters to Latin
    arabic_to_latin = {
        "ا": "a",
        "أ": "a",
        "إ": "i",
        "آ": "a",
        "ب": "b",
        "ت": "t",
        "ث": "th",
        "ج": "j",
        "ح": "h",
        "خ": "kh",
        "د": "d",
        "ذ": "dh",
        "ر": "r",
        "ز": "z",
        "س": "s",
        "ش": "sh",
        "ص": "s",
        "ض": "d",
        "ط": "t",
        "ظ": "z",
        "ع": "a",
        "غ": "gh",
        "ف": "f",
        "ق": "q",
        "ك": "k",
        "ل": "l",
        "م": "m",
        "ن": "n",
        "ه": "h",
        "و": "w",
        "ي": "y",
        "ى": "a",
        "ة": "h",
        "ء": "",
        "ؤ": "w",
        "ئ": "y",
        "ـ": "",
        "َ": "a",
        "ُ": "u",
        "ِ": "i",
        "ْ": "",
        "ّ": "",
        "ٰ": "a",
        "ً": "an",
        "ٌ": "un",
        "ٍ": "in",
        "ٓ": "",
        "ٖ": "",
        "ٗ": "",
        "٘": "",
        "ٙ": "",
        "ٚ": "",
        "ٛ": "",
        "ٜ": "",
        "ٝ": "",
        "ٞ": "",
        "ٟ": "",
        "ﺕ": "t",  # Arabic letter tah isolated form
        "ﺗ": "t",  # Arabic letter tah initial form
        "ﺘ": "t",  # Arabic letter tah medial form
        "ﺖ": "t",  # Arabic letter tah final form
    }

    # Convert Cyrillic and Arabic characters
    transliterated = []
    for char in result:
        if char in cyrillic_to_latin:
            transliterated.append(cyrillic_to_latin[char])
        elif char in arabic_to_latin:
            transliterated.append(arabic_to_latin[char])
        else:
            transliterated.append(char)

    return "".join(transliterated)


class TopicValidationError(Exception):
    """Exception for topic validation errors."""

    pass


class TopicValidator:
    """Validator for topic extraction results."""

    def __init__(self, config: Optional[TopicConfig] = None):
        self.config = config or TopicConfig()

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

            # Normalize name: remove accents, convert to lowercase, and strip whitespace
            name = name.strip()
            normalized_name = remove_accents(name).lower()

            # Replace colons with underscores (e.g., "contexto_cultural_de_lucas_16:18" -> "contexto_cultural_de_lucas_16_18")
            normalized_name = normalized_name.replace(":", "_")

            # Replace spaces with underscores (e.g., "herança espiritual dos filhos de Deus" -> "heranca_espiritual_dos_filhos_de_deus")
            normalized_name = normalized_name.replace(" ", "_")

            # Remove parentheses and their contents (e.g., "atividade física regular (ciclismo, flexão, prancha)" -> "atividade_fisica_regular")
            # First remove parentheses and everything inside them
            normalized_name = re.sub(r"\([^)]*\)", "", normalized_name)

            # Replace periods with underscores (e.g., "estudo_de_n.t._wright_sobre_casamento" -> "estudo_de_n_t_wright_sobre_casamento")
            normalized_name = normalized_name.replace(".", "_")

            # Then clean up any double underscores or trailing underscores
            normalized_name = re.sub(r"_+", "_", normalized_name)
            normalized_name = normalized_name.strip("_")

            # Check for snake_case (using normalized name)
            # Allow Portuguese characters (with accents removed), hyphens, and underscores
            # Original: ^[a-z][a-z0-9_]*$ - too strict for Portuguese content
            # New: ^[a-z][a-z0-9_-]*$ - allows hyphens and underscores
            if not re.match(r"^[a-z][a-z0-9_-]*$", normalized_name):
                raise TopicValidationError(
                    f"Topic {i}: name '{name}' must be snake_case (letters, numbers, hyphens, underscores)"
                )

            # Update topic name to normalized version
            topic["name"] = normalized_name

            # Check for duplicates
            if normalized_name in seen_names:
                raise TopicValidationError(f"Topic {i}: Duplicate name '{name}'")
            seen_names.add(normalized_name)

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
