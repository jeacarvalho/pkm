"""CDU mapping utilities for fallback classification."""

from pathlib import Path
from typing import Optional, Dict

CDU_FOLDER_MAPPING: Dict[str, Dict[str, str]] = {
    "00": {"cdu": "000", "description": "Generalidades"},
    "10": {"cdu": "004", "description": "Computação, informática"},
    "20": {"cdu": "2", "description": "Religião"},
    "30": {"cdu": "658", "description": "Gestão, liderança e administração"},
    "40": {"cdu": "159.9", "description": "Psicologia cognitiva e aprendizado"},
    "50": {"cdu": "613", "description": "Saúde geral"},
    "60": {"cdu": "657", "description": "Contabilidade"},
    "70": {"cdu": "330", "description": "Economia"},
    "80": {"cdu": "316", "description": "Sociologia"},
    "90": {"cdu": "316.3", "description": "Família e relacionamentos"},
    "100": {"cdu": "01", "description": "Bibliografia"},
    "110": {"cdu": "658", "description": "Gestão e administração de empresas"},
    "120": {"cdu": "1", "description": "Filosofia"},
    "130": {"cdu": "929", "description": "Biografias"},
    "140": {"cdu": "34", "description": "Direito"},
    "150": {"cdu": "300", "description": "Ciências sociais"},
}

KEYWORD_CDU_MAPPING: Dict[str, str] = {
    "líder": "658.4",
    "liderança": "658.4",
    "gestão": "658",
    "gestao": "658",
    "administração": "658",
    "administracao": "658",
    "contabilidade": "657",
    "contabilidade": "657",
    "economia": "330",
    "finanças": "336",
    "financas": "336",
    "dinheiro": "336",
    "saúde": "613",
    "saude": "613",
    "medicina": "61",
    "alimentação": "613",
    "alimentacao": "613",
    "exercício": "613",
    "exercicio": "613",
    "filosofia": "1",
    "teologia": "2",
    "religião": "2",
    "religiao": "2",
    "bíblia": "22",
    "biblia": "22",
    "história": "9",
    "historia": "9",
    "ciência": "5",
    "ciencia": "5",
    "tecnologia": "004",
    "software": "004",
    "computação": "004",
    "computacao": "004",
    "ia": "004",
    "ai": "004",
    "chatgpt": "004",
    "psicologia": "159",
    "mente": "159",
    "cognição": "159.9",
    "cognicao": "159.9",
    "aprendizado": "159.9",
    "aprendizagem": "159.9",
    "educação": "37",
    "educacao": "37",
    "escola": "37",
    "universidade": "378",
    "música": "78",
    "musica": "78",
    "arte": "7",
    "direito": "34",
    "lei": "34",
    "legislação": "34",
    "legislacao": "34",
    "família": "316.3",
    "familia": "316.3",
    "criança": "316.3",
    "crianca": "316.3",
    "comunidade": "316",
    "sociedade": "316",
    "política": "32",
    "politica": "32",
    "governo": "35",
    "empresa": "658",
    "empreendedorismo": "658.1",
    "trabalho": "331",
    "carreira": "658.3",
    "investimento": "336",
    "marketing": "658.8",
    "vendas": "658.8",
    "rh": "658.3",
    "recursos_humanos": "658.3",
}


def infer_cdu_from_folder(folder_path: str) -> Optional[str]:
    """Infer CDU from folder name.

    Args:
        folder_path: Full path to the folder

    Returns:
        CDU code string or None if not found
    """
    path = Path(folder_path)
    folder_name = path.name

    # Extract numeric prefix (e.g., "30 LIDERANCA" -> "30")
    prefix = folder_name.split()[0] if folder_name.split() else ""

    if prefix in CDU_FOLDER_MAPPING:
        return CDU_FOLDER_MAPPING[prefix]["cdu"]

    return None


def infer_cdu_from_keywords(text: str) -> Optional[str]:
    """Infer CDU from keywords in note title or content.

    Args:
        text: Title or content of the note

    Returns:
        CDU code string or None if not found
    """
    text_lower = text.lower()

    for keyword, cdu in KEYWORD_CDU_MAPPING.items():
        if keyword in text_lower:
            return cdu

    return None


def infer_cdu_fallback(note_path: str) -> str:
    """Infer CDU from note path using folder and keywords.

    Args:
        note_path: Full path to the note file

    Returns:
        Inferred CDU code, or empty string if no inference possible
    """
    # Try folder first
    folder_cdu = infer_cdu_from_folder(str(Path(note_path).parent))
    if folder_cdu:
        return folder_cdu

    # Try keywords in filename
    filename = Path(note_path).stem
    keyword_cdu = infer_cdu_from_keywords(filename)
    if keyword_cdu:
        return keyword_cdu

    # Return empty string if no match
    return ""


def get_cdu_description(cdu: str) -> Optional[str]:
    """Get description for a CDU code.

    Args:
        cdu: CDU code (e.g., "658.4")

    Returns:
        Description string or None
    """
    # Map specific CDUs to descriptions
    cdu_descriptions = {
        "000": "Generalidades",
        "004": "Computação e informática",
        "1": "Filosofia",
        "2": "Religião",
        "22": "Bíblia",
        "30": "Ciências sociais",
        "316": "Sociologia",
        "316.3": "Família e sociologia",
        "330": "Economia",
        "331": "Trabalho",
        "34": "Direito",
        "35": "Administração pública",
        "37": "Educação",
        "378": "Ensino superior",
        "5": "Ciências puras",
        "61": "Medicina",
        "613": "Saúde",
        "65": "Gestão",
        "657": "Contabilidade",
        "658": "Gestão e administração",
        "658.1": "Empreendedorismo",
        "658.3": "Recursos humanos",
        "658.4": "Liderança",
        "658.8": "Marketing e vendas",
        "7": "Arte",
        "78": "Música",
        "9": "História",
        "01": "Bibliografia",
        "159": "Psicologia",
        "159.9": "Psicologia cognitiva",
        "929": "Biografias",
    }

    if cdu in cdu_descriptions:
        return cdu_descriptions[cdu]

    # Check folder mappings first
    prefix = cdu.split(".")[0]
    if len(prefix) <= 2 and prefix in CDU_FOLDER_MAPPING:
        return CDU_FOLDER_MAPPING[prefix]["description"]

    return None
