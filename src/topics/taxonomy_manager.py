"""Taxonomy manager for CDU (Universal Decimal Classification)."""

from typing import Dict, List, Optional


class CDUManager:
    """Manager for CDU classification lookup and validation."""

    # Common CDU classifications with descriptions
    CDU_LOOKUP: Dict[str, str] = {
        # Philosophy
        "1": "Filosofia",
        "10": "Metafísica",
        "11": "Cosmologia",
        "12": "Gnosiologia",
        "13": "Psicologia",
        "14": "Filosofia dos valores",
        "159.9": "Psicologia",
        "16": "Lógica",
        "17": "Moral",
        # Religion
        "2": "Religião",
        "21": "Religião pré-histórica e religiões de povos primitivos",
        "22": "Bíblia",
        "23": "Teologia",
        "24": "Teologia moral",
        # Social Sciences
        "3": "Ciências sociais",
        "30": "Sociologia",
        "305": "Sociologia. Sociedade",
        "305.8": "Grupos minoritários",
        "31": "Demografia",
        "32": "Política",
        "321": "Teoria do Estado",
        "321.1": "Sistemas políticos",
        "33": "Economia",
        "34": "Direito",
        "35": "Administração pública",
        "36": "Segurança",
        # Language and Literature
        "37": "Educação",
        "378": "Ensino superior",
        # History
        "9": "Geografia. História",
        "91": "Geografia",
        "93": "História antiga",
        "94": "História medieval",
        "95": "História moderna",
        # Specific subjects
        "159.9": "Psicologia",
        "316": "Sociologia",
    }

    @classmethod
    def validate_cdu_format(cls, cdu: str) -> bool:
        """Validate CDU format (supports multiple levels: XXX.X, XXX.XX.XX, etc.)."""
        if not cdu:
            return False

        # Remove any whitespace
        cdu = cdu.strip()

        # Handle programming language suffixes (e.g., "004.43 RUST", "004.43RUST")
        # Extract just the numeric part for validation
        import re

        match = re.search(r"(\d+(?:\.\d+)*)", cdu)
        if match:
            cdu = match.group(1)
        else:
            # If no numeric part found, check if it's a valid single digit
            if cdu.isdigit() and 1 <= len(cdu) <= 3:
                return True
            return False

        # Handle apostrophe format (e.g., "81'25")
        if "'" in cdu:
            # Replace apostrophe with dot for validation
            cdu = cdu.replace("'", ".")

        # Handle colon format (e.g., "27-7:324")
        if ":" in cdu:
            # Replace colon with dot for validation
            cdu = cdu.replace(":", ".")

        # Check for parentheses format (e.g., "94(37)", "94(813.2)", "7.03(81)")
        if "(" in cdu and ")" in cdu:
            # Extract main class and auxiliary
            main_part = cdu.split("(")[0].strip()
            aux_part = cdu.split("(")[1].split(")")[0].strip()

            # Validate main part (should be digits or digits with dots)
            if not cls._is_valid_cdu_part(main_part):
                return False

            # Validate auxiliary part (can have dots for decimals inside parentheses)
            if not cls._is_valid_cdu_part(aux_part):
                return False

            return True

        # Standard format: should be like "321.1", "305.8", "330.341.5"
        parts = cdu.split(".")

        # Special case: single part after replacements (e.g., "27" from "27-7:324" after replacements)
        if len(parts) == 1:
            # Check if it's a valid single digit part (1-3 digits)
            if parts[0].isdigit() and 1 <= len(parts[0]) <= 3:
                return True
            return False

        # Must have at least 2 parts (main class + subclass)
        if len(parts) < 2:
            return False

        # First part should be 1-3 digits (main class)
        if not parts[0].isdigit() or len(parts[0]) > 3 or len(parts[0]) < 1:
            return False

        # All subsequent parts should be 1-4 digits (subclasses)
        for part in parts[1:]:
            if not part.isdigit() or len(part) > 4 or len(part) < 1:
                return False

        return True

    @classmethod
    def _is_valid_cdu_part(cls, part: str) -> bool:
        """Check if a CDU part is valid (digits or digits with dots)."""
        if not part:
            return False

        # Split by dots to handle decimal parts
        subparts = part.split(".")

        # First subpart should be digits
        if not subparts[0].isdigit() or len(subparts[0]) > 4 or len(subparts[0]) < 1:
            return False

        # All subsequent subparts should be digits
        for subpart in subparts[1:]:
            if not subpart.isdigit() or len(subpart) > 4 or len(subpart) < 1:
                return False

        return True

    @classmethod
    def normalize_cdu(cls, cdu: str) -> Optional[str]:
        """Normalize CDU format while preserving depth.

        Fixes common issues:
        - "32" becomes "32.0" (adds missing decimal for single numbers)
        - Preserves existing multi-level classifications (e.g., 330.341.5 stays as is)
        - Converts parentheses format "94(37)" to standard format "94.37"
        - Handles apostrophe format "81'25" -> "81.25"
        - Handles colon format "27-7:324" -> "27.7.324"
        - Handles programming language suffixes (e.g., "004.43 RUST" -> "004.43")

        Args:
            cdu: Raw CDU string from API

        Returns:
            Normalized CDU string or None if cannot normalize
        """
        if not cdu:
            return None

        cdu = cdu.strip()

        # Handle programming language suffixes (e.g., "004.43 RUST", "004.43RUST")
        # Extract just the numeric part for normalization
        import re

        match = re.search(r"(\d+(?:\.\d+)*)", cdu)
        if match:
            cdu = match.group(1)
        else:
            # If no numeric part found, check if it's a valid single digit
            if cdu.isdigit() and 1 <= len(cdu) <= 3:
                return f"{cdu}.0"
            return None

        # Fix: Convert apostrophe to dot (e.g., "81'25" -> "81.25")
        if "'" in cdu:
            cdu = cdu.replace("'", ".")

        # Fix: Convert colon to dot (e.g., "27-7:324" -> "27.7.324")
        if ":" in cdu:
            cdu = cdu.replace(":", ".")

        # Fix: Convert hyphen format to dot format (e.g., "27-28" -> "27.28")
        if "-" in cdu and "." not in cdu:
            cdu = cdu.replace("-", ".")

        # Fix: Convert hyphen after decimal point (e.g., "821.111-34" -> "821.111.34")
        if "-" in cdu and "." in cdu:
            cdu = cdu.replace("-", ".")

        # Check if already valid (supports multi-level and parentheses)
        if cls.validate_cdu_format(cdu):
            # Convert parentheses format to standard format
            if "(" in cdu and ")" in cdu:
                main_part = cdu.split("(")[0].strip()
                aux_part = cdu.split("(")[1].split(")")[0].strip()
                return f"{main_part}.{aux_part}"
            return cdu

        parts = cdu.split(".")

        # Case 1: No decimal point (e.g., "32") - add .0
        if len(parts) == 1:
            if parts[0].isdigit() and 1 <= len(parts[0]) <= 3:
                return f"{parts[0]}.0"
            return None

        # Case 2: Has decimals but invalid format - don't truncate
        # Multi-level CDUs are now valid (e.g., 330.341.5)
        return None

    @classmethod
    def get_description(cls, cdu: str) -> Optional[str]:
        """Get description for a CDU classification."""
        if not cls.validate_cdu_format(cdu):
            return None

        # Try exact match first
        if cdu in cls.CDU_LOOKUP:
            return cls.CDU_LOOKUP[cdu]

        # Try parent category
        parts = cdu.split(".")
        for i in range(len(parts) - 1, 0, -1):
            parent = ".".join(parts[:i])
            if parent in cls.CDU_LOOKUP:
                return f"{cls.CDU_LOOKUP[parent]} (subclassificado)"

        return None

    @classmethod
    def validate_cdu_list(cls, cdu_list: List[str]) -> List[str]:
        """Validate and filter a list of CDU codes."""
        valid = []
        for cdu in cdu_list:
            normalized = cls.normalize_cdu(cdu)
            if normalized:
                valid.append(normalized)
        return valid
