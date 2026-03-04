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
        """Validate CDU format (XXX.X or XX.X or X.X)."""
        if not cdu:
            return False

        # Remove any whitespace
        cdu = cdu.strip()

        # Check format: should be like "321.1" or "305.8"
        parts = cdu.split(".")
        if len(parts) != 2:
            return False

        # First part should be 1-3 digits
        if not parts[0].isdigit() or len(parts[0]) > 3 or len(parts[0]) < 1:
            return False

        # Second part should be 1-2 digits
        if not parts[1].isdigit() or len(parts[1]) > 2:
            return False

        return True

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
    def normalize_cdu(cls, cdu: str) -> Optional[str]:
        """Normalize CDU format."""
        if not cdu:
            return None

        cdu = cdu.strip()

        if cls.validate_cdu_format(cdu):
            return cdu

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
