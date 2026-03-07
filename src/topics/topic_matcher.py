"""
Topic Matching Engine - Sprint 10
Match entre tópicos do capítulo e tópicos das notas do vault
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from thefuzz import fuzz  # Fuzzy matching

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .config import TopicConfig
from .topic_normalization import TopicNormalizer


class TopicMatcher:
    """Motor de matching por sobreposição de tópicos"""

    def __init__(self, config: TopicConfig):
        self.config = config
        self.logger = self._setup_logger()
        self.fuzzy_threshold = (
            40  # Threshold para fuzzy match (reduzido para encontrar mais matches)
        )
        self.normalizer = TopicNormalizer()  # Topic normalizer

        # Skip list - notas com frontmatter inválido (não tenta ler novamente)
        self._skip_notes = set()

        # Estatísticas
        self.stats = {
            "total_notes_scanned": 0,
            "notes_with_topics": 0,
            "notes_matched": 0,
            "start_time": None,
            "end_time": None,
        }

    def _setup_logger(self) -> logging.Logger:
        """Configura logging para arquivo e console"""
        self.config.create_log_dir()

        logger = logging.getLogger("topic_matcher")
        logger.setLevel(logging.INFO)

        # File handler - matcher.log
        log_file = self.config.log_dir / "matcher.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # Error file handler
        error_file = self.config.log_dir / "errors.log"
        error_handler = logging.FileHandler(error_file, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        logger.addHandler(console_handler)

        return logger

    def _load_chapter_topics(self, chapter_topics_path: Path) -> Optional[Dict]:
        """Carrega JSON de tópicos do capítulo"""
        try:
            with open(chapter_topics_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Suporta dois formatos:
            # 1. Lista direta de tópicos: [{"name": "...", "weight": ...}, ...]
            # 2. Dict com metadados: {"topics": [...], "chapter_title": "..."}
            if isinstance(data, list):
                return {"topics": data, "chapter_title": chapter_topics_path.stem}
            elif isinstance(data, dict):
                return data
            else:
                self.logger.error(f"Invalid chapter topics format: {type(data)}")
                return None

        except Exception as e:
            self.logger.error(f"Error loading chapter topics: {str(e)}")
            return None

    def _read_note_frontmatter(self, note_path: Path) -> Optional[Dict]:
        """Lê frontmatter de uma nota (apenas topic_classification)"""
        import yaml

        # Check skip list
        if str(note_path) in self._skip_notes:
            return None

        try:
            with open(note_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extrai frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    return frontmatter

            return {}

        except Exception as e:
            # Add to skip list to avoid repeated errors
            self._skip_notes.add(str(note_path))
            self.logger.error(f"Error reading frontmatter {note_path}: {str(e)}")
            return None

    def _fuzzy_match(self, topic1: str, topic2: str) -> Tuple[bool, int]:
        """
        Verifica se dois tópicos são similares via fuzzy matching

        Returns:
            (is_match, score)
        """
        # Token ratio (mais rigoroso)
        score = fuzz.token_sort_ratio(topic1.lower(), topic2.lower())

        return score >= self.fuzzy_threshold, score

    def _calculate_match_score(
        self,
        chapter_topics: List[Dict],
        vault_topics: List[Dict],
        chapter_cdu_primary: Optional[str] = None,
        chapter_cdu_secondary: Optional[List[str]] = None,
        vault_cdu_primary: Optional[str] = None,
        vault_cdu_secondary: Optional[List[str]] = None,
        use_normalization: bool = True,
    ) -> Dict:
        """
        Calcula score de matching entre tópicos do capítulo e do vault.

        Algoritmo:
        1. Normaliza tópicos do capítulo para categorias mais amplas
        2. Fuzzy match entre tópicos do capítulo e do vault
        3. Bônus de score por matching de CDU
        4. Normaliza score para 0-100
        """
        # Step 1: Normalize chapter topics
        normalized_topics = self._normalize_chapter_topics(
            chapter_topics, use_normalization
        )

        # Step 2: Match topics
        topic_score, matched_topics = self._match_topics(
            normalized_topics, vault_topics
        )

        # Step 3: Calculate CDU bonuses
        cdu_bonus, cdu_matches = self._calculate_cdu_bonus(
            chapter_cdu_primary,
            chapter_cdu_secondary,
            vault_cdu_primary,
            vault_cdu_secondary,
        )

        # Step 4: Calculate final score
        total_score = topic_score + cdu_bonus
        all_matches = matched_topics + cdu_matches

        return self._normalize_final_score(
            total_score, cdu_bonus, all_matches, chapter_topics
        )

    def _normalize_chapter_topics(
        self, chapter_topics: List[Dict], use_normalization: bool
    ) -> List[Dict]:
        """Normaliza tópicos do capítulo se habilitado."""
        if not use_normalization:
            return chapter_topics

        normalized = self.normalizer.normalize_topics(chapter_topics)
        self.logger.debug(
            f"Normalized {len(chapter_topics)} topics to {len(normalized)} topics"
        )
        return normalized

    def _match_topics(
        self, chapter_topics: List[Dict], vault_topics: List[Dict]
    ) -> Tuple[int, List[Dict]]:
        """
        Faz matching fuzzy entre tópicos do capítulo e do vault.

        Returns:
            Tuple of (total_score, matched_topics_list)
        """
        total_score = 0
        matched = []

        for ch_topic in chapter_topics:
            match = self._find_single_topic_match(ch_topic, vault_topics)
            if match:
                total_score += match["weight"]
                matched.append(match)

        return total_score, matched

    def _find_single_topic_match(
        self, ch_topic: Dict, vault_topics: List[Dict]
    ) -> Optional[Dict]:
        """
        Encontra o melhor match para um único tópico do capítulo.

        Returns:
            Match dictionary se encontrado, None caso contrário
        """
        ch_name = ch_topic.get("name", "")
        ch_weight = ch_topic.get("weight", 5)
        is_normalized = ch_topic.get("is_normalized", False)
        original_topic = ch_topic.get("original_topic", "")

        for vt_topic in vault_topics:
            vt_name = vt_topic.get("name", "")
            vt_weight = vt_topic.get("weight", 5)

            is_match, fuzzy_score = self._fuzzy_match(ch_name, vt_name)

            if is_match:
                match_score = self._calculate_match_weight(
                    ch_weight, vt_weight, is_normalized
                )

                return self._create_match_dict(
                    ch_name,
                    vt_name,
                    original_topic,
                    match_score,
                    fuzzy_score,
                    is_normalized,
                )

        return None

    def _calculate_match_weight(
        self, ch_weight: int, vt_weight: int, is_normalized: bool
    ) -> int:
        """Calcula peso do match baseado nos pesos dos tópicos."""
        if is_normalized:
            return max(1, min(ch_weight, vt_weight) // 2)
        return min(ch_weight, vt_weight)

    def _create_match_dict(
        self,
        ch_name: str,
        vt_name: str,
        original_topic: str,
        match_score: int,
        fuzzy_score: int,
        is_normalized: bool,
    ) -> Dict:
        """Cria dicionário de match."""
        chapter_topic_display = (
            f"{ch_name} [from: {original_topic}]" if is_normalized else ch_name
        )
        match_type = "topic_normalized" if is_normalized else "topic"

        return {
            "chapter_topic": chapter_topic_display,
            "vault_topic": vt_name,
            "weight": match_score,
            "fuzzy_score": fuzzy_score,
            "match_type": match_type,
            "is_normalized": is_normalized,
        }

    def _calculate_cdu_bonus(
        self,
        chapter_cdu_primary: Optional[str],
        chapter_cdu_secondary: Optional[List[str]],
        vault_cdu_primary: Optional[str],
        vault_cdu_secondary: Optional[List[str]],
    ) -> Tuple[int, List[Dict]]:
        """
        Calcula bônus de matching por CDU.

        Returns:
            Tuple of (total_cdu_bonus, cdu_matches_list)
        """
        cdu_bonus = 0
        cdu_matches = []

        # Match CDU primário
        primary_bonus, primary_matches = self._match_primary_cdu(
            chapter_cdu_primary, vault_cdu_primary
        )
        cdu_bonus += primary_bonus
        cdu_matches.extend(primary_matches)

        # Match CDU secundário
        secondary_bonus, secondary_matches = self._match_secondary_cdu(
            chapter_cdu_secondary, vault_cdu_secondary
        )
        cdu_bonus += secondary_bonus
        cdu_matches.extend(secondary_matches)

        return cdu_bonus, cdu_matches

    def _match_primary_cdu(
        self, chapter_cdu: Optional[str], vault_cdu: Optional[str]
    ) -> Tuple[int, List[Dict]]:
        """Match CDU primário com bônus para match exato ou categoria."""
        if not chapter_cdu or not vault_cdu:
            return 0, []

        # Match exato
        if chapter_cdu == vault_cdu:
            return 20, [
                {
                    "chapter_topic": f"CDU: {chapter_cdu}",
                    "vault_topic": f"CDU: {vault_cdu}",
                    "weight": 20,
                    "fuzzy_score": 100,
                    "match_type": "cdu_primary_exact",
                }
            ]

        # Match de categoria (primeiros dígitos)
        ch_main = self._extract_cdu_category(chapter_cdu)
        vt_main = self._extract_cdu_category(vault_cdu)

        if ch_main == vt_main:
            return 10, [
                {
                    "chapter_topic": f"CDU: {chapter_cdu}",
                    "vault_topic": f"CDU: {vault_cdu}",
                    "weight": 10,
                    "fuzzy_score": 100,
                    "match_type": "cdu_primary_category",
                }
            ]

        return 0, []

    def _extract_cdu_category(self, cdu: str) -> str:
        """Extrai categoria principal do CDU (primeiros dígitos)."""
        cdu_str = str(cdu)
        if "." in cdu_str:
            return cdu_str.split(".")[0]
        return cdu_str[:2]

    def _match_secondary_cdu(
        self,
        chapter_secondary: Optional[List[str]],
        vault_secondary: Optional[List[str]],
    ) -> Tuple[int, List[Dict]]:
        """Match CDU secundários comuns."""
        if not chapter_secondary or not vault_secondary:
            return 0, []

        common = set(chapter_secondary) & set(vault_secondary)
        if not common:
            return 0, []

        bonus = len(common) * 5
        matches = [
            {
                "chapter_topic": f"CDU_sec: {cdu}",
                "vault_topic": f"CDU_sec: {cdu}",
                "weight": 5,
                "fuzzy_score": 100,
                "match_type": "cdu_secondary",
            }
            for cdu in common
        ]

        return bonus, matches

    def _normalize_final_score(
        self,
        total_score: int,
        cdu_bonus: int,
        matched_topics: List[Dict],
        chapter_topics: List[Dict],
    ) -> Dict:
        """Normaliza score final para escala 0-100."""
        max_possible = sum(t.get("weight", 5) for t in chapter_topics) + 30
        normalized = (total_score / max_possible * 100) if max_possible > 0 else 0

        return {
            "score": round(normalized, 2),
            "raw_score": total_score,
            "cdu_bonus": cdu_bonus,
            "max_possible": max_possible,
            "matched_topics": matched_topics,
            "total_chapter_topics": len(chapter_topics),
            "total_matched": len(matched_topics),
        }

    def _find_notes_with_topics(self, vault_dir: Path) -> List[Path]:
        """Encontra todas as notas .md no vault"""
        notes = []

        for md_file in vault_dir.rglob("*.md"):
            # Ignora arquivos do sistema
            if md_file.name.startswith("."):
                continue
            # Ignora pasta .obsidian
            if ".obsidian" in str(md_file):
                continue
            # Ignora pasta de Livros processados (capítulos já tem seus próprios matches)
            if "/Livros/" in str(md_file) or "\\Livros\\" in str(md_file):
                continue

            notes.append(md_file)

        return notes

    def _extract_cdu_from_chapter_topics(
        self, chapter_topics: List[Dict]
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        """Extrai CDU primário e secundário dos tópicos do capítulo"""
        from collections import Counter

        # Extrai todos os CDUs dos tópicos (filtra valores None)
        chapter_cdus: List[str] = []
        for t in chapter_topics:
            cdu = t.get("cdu")
            if cdu:  # Filtra valores None ou vazios
                chapter_cdus.append(cdu)

        if not chapter_cdus:
            return None, []

        # Determina CDU primário (mais frequente)
        cdu_counter = Counter(chapter_cdus)
        most_common_cdu, count = cdu_counter.most_common(1)[0]

        # Se aparece pelo menos 2 vezes, considera primário
        if count >= 2:
            chapter_cdu_primary = most_common_cdu
            chapter_cdu_secondary = [
                cdu for cdu in chapter_cdus if cdu != chapter_cdu_primary
            ]
        else:
            # Se nenhum CDU aparece múltiplas vezes, usa o primeiro como primário
            chapter_cdu_primary = chapter_cdus[0]
            chapter_cdu_secondary = chapter_cdus[1:] if len(chapter_cdus) > 1 else []

        return chapter_cdu_primary, chapter_cdu_secondary

    def match_chapter_to_vault(
        self,
        chapter_topics: List[Dict],
        vault_dir: Path,
        top_k: int = 20,
        threshold: float = 0.0,
        use_normalization: bool = True,
    ) -> List[Dict]:
        """
        Match tópicos do capítulo contra todas as notas do vault

        Returns:
            Lista de matches ordenada por score (Top-K)
        """
        # Encontra todas as notas
        notes = self._find_notes_with_topics(vault_dir)

        self.stats["total_notes_scanned"] = len(notes)
        self.logger.info(f"📊 Scanning {len(notes)} notes in vault...")

        # Extrai CDUs do capítulo
        chapter_cdu_primary, chapter_cdu_secondary = (
            self._extract_cdu_from_chapter_topics(chapter_topics)
        )

        if chapter_cdu_primary:
            self.logger.info(f"📚 Chapter primary CDU: {chapter_cdu_primary}")
        if chapter_cdu_secondary:
            self.logger.info(f"📚 Chapter secondary CDUs: {chapter_cdu_secondary}")

        matches = []

        for i, note_path in enumerate(notes, 1):
            if i % 500 == 0:
                self.logger.info(f"📈 Progress: {i}/{len(notes)}")

            # Lê frontmatter
            frontmatter = self._read_note_frontmatter(note_path)

            if not frontmatter:
                continue

            # Verifica se tem topic_classification
            topic_classification = frontmatter.get("topic_classification", {})

            if not topic_classification:
                # Fallback: nota sem tópicos (ignora ou score 0)
                continue

            self.stats["notes_with_topics"] += 1

            vault_topics = topic_classification.get("topics", [])
            vault_cdu_primary = topic_classification.get("cdu_primary")
            vault_cdu_secondary = topic_classification.get("cdu_secondary", [])

            if not vault_topics:
                continue

            # Calcula match score com CDUs
            match_result = self._calculate_match_score(
                chapter_topics,
                vault_topics,
                chapter_cdu_primary=chapter_cdu_primary,
                chapter_cdu_secondary=chapter_cdu_secondary,
                vault_cdu_primary=vault_cdu_primary,
                vault_cdu_secondary=vault_cdu_secondary,
                use_normalization=use_normalization,
            )

            # Filtra por threshold (exclui scores zero ou muito baixos)
            if match_result["score"] < threshold or match_result["score"] < 0.1:
                continue

            # Adiciona metadata da nota
            match_result["note_path"] = str(note_path)
            match_result["note_title"] = note_path.stem
            match_result["note_name"] = note_path.name

            matches.append(match_result)
            self.stats["notes_matched"] += 1

        # Ordena por score (descendente)
        matches.sort(key=lambda x: x["score"], reverse=True)

        # Retorna Top-K
        return matches[:top_k]

    def run(
        self,
        chapter_topics_path: Path,
        vault_dir: Path,
        output_path: Optional[Path] = None,
        top_k: int = 20,
        threshold: float = 10.0,
        use_normalization: bool = True,
    ) -> Dict:
        """
        Executa matching completo

        Returns:
            Dict com resultados e estatísticas
        """
        # Carrega tópicos do capítulo
        chapter_data = self._load_chapter_topics(chapter_topics_path)

        if not chapter_data:
            self.logger.error("Failed to load chapter topics")
            return {"error": "Failed to load chapter topics"}

        chapter_topics = chapter_data.get("topics", [])
        chapter_title = chapter_data.get("chapter_title", "Unknown")

        if not chapter_topics:
            self.logger.error("No topics found in chapter JSON")
            return {"error": "No topics in chapter"}

        self.stats["start_time"] = datetime.now()

        self.logger.info(f"🚀 Starting topic matching...")
        self.logger.info(f"📖 Chapter: {chapter_title}")
        self.logger.info(f"📁 Vault: {vault_dir}")
        self.logger.info(f"🎯 Top-K: {top_k}")
        self.logger.info(f"📏 Threshold: {threshold}")

        # Executa matching
        matches = self.match_chapter_to_vault(
            chapter_topics=chapter_topics,
            vault_dir=vault_dir,
            top_k=top_k,
            threshold=threshold,
            use_normalization=use_normalization,
        )

        self.stats["end_time"] = datetime.now()

        # Monta resultado
        result = {
            "chapter": chapter_title,
            "chapter_topics": chapter_topics,
            "matches": matches,
            "total_notes_scanned": self.stats["total_notes_scanned"],
            "notes_with_topics": self.stats["notes_with_topics"],
            "total_matches_found": len(matches),
            "threshold": threshold,
            "top_k": top_k,
            "processed_at": datetime.now().isoformat(),
        }

        # Loga estatísticas
        self._log_stats(result)

        # Salva output se especificado
        if output_path:
            self._save_result(result, output_path)

        return result

    def _save_result(self, result: Dict, output_path: Path):
        """Salva resultado em arquivo JSON"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        self.logger.info(f"💾 Results saved to: {output_path}")

    def _log_stats(self, result: Dict):
        """Loga estatísticas finais"""
        duration = self.stats["end_time"] - self.stats["start_time"]

        self.logger.info("=" * 60)
        self.logger.info("📊 MATCHING COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Total notes scanned: {result['total_notes_scanned']}")
        self.logger.info(f"Notes with topics: {result['notes_with_topics']}")
        self.logger.info(f"Total matches found: {result['total_matches_found']}")
        self.logger.info(f"Top-K returned: {len(result['matches'])}")
        self.logger.info(f"Duration: {duration}")

        if result["matches"]:
            top_match = result["matches"][0]
            self.logger.info(
                f"🏆 Top match: {top_match['note_title']} (score: {top_match['score']})"
            )


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Sprint 10: Topic Matching Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (1 capítulo)
  python3 -m src.topics.topic_matcher \\
    --chapter-topics "data/test/capitulo_01_topics.json" \\
    --vault-dir "/home/s015533607/MEGAsync/Minhas_notas" \\
    --dry-run \\
    --top-k 20

  # Modo real (1 capítulo)
  python3 -m src.topics.topic_matcher \\
    --chapter-topics "data/test/capitulo_01_topics.json" \\
    --vault-dir "/home/s015533607/MEGAsync/Minhas_notas" \\
    --output "data/matches/capitulo_01_matches.json" \\
    --top-k 20 \\
    --threshold 10.0

  # Livro completo (após teste piloto)
  python3 -m src.topics.topic_matcher \\
    --chapter-topics "data/processed/all_chapters_topics.json" \\
    --vault-dir "/home/s015533607/MEGAsync/Minhas_notas" \\
    --output "data/matches/book_matches.json"
        """,
    )

    parser.add_argument(
        "--chapter-topics",
        type=str,
        required=True,
        help="JSON com tópicos do capítulo (obrigatório)",
    )

    parser.add_argument(
        "--vault-dir",
        type=str,
        required=True,
        help="Diretório do vault Obsidian (obrigatório)",
    )

    parser.add_argument(
        "--output", type=str, default=None, help="Arquivo de saída JSON (opcional)"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Apenas log, não salva resultados"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="Número de matches para retornar (default: 20)",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=10.0,
        help="Score mínimo para considerar match (default: 10.0)",
    )

    args = parser.parse_args()

    # Configura
    config = TopicConfig()

    # Cria matcher
    matcher = TopicMatcher(config)

    # Executa
    chapter_topics_path = Path(args.chapter_topics)
    vault_dir = Path(args.vault_dir)
    output_path = Path(args.output) if args.output else None

    result = matcher.run(
        chapter_topics_path=chapter_topics_path,
        vault_dir=vault_dir,
        output_path=output_path if not args.dry_run else None,
        top_k=args.top_k,
        threshold=args.threshold,
    )

    # Return code
    if "error" in result:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
