"""Vault Properties Writer - Sprint 09.

Escreve tópicos extraídos (Sprint 08) no frontmatter das notas do vault.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from src.topics.config import TopicConfig
from src.topics.cdu_resolver import infer_cdu_fallback, get_cdu_description
from src.utils.logging import get_logger

logger = get_logger(__name__)


class VaultWriter:
    """Escreve properties de tópicos no frontmatter das notas."""

    def __init__(self, config: TopicConfig):
        self.config = config
        self._setup_logger()

        # Estatísticas
        self.stats = {
            "total_jsons": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "modified": [],
        }

    def _setup_logger(self):
        """Configura logging para arquivo e console."""
        # Cria diretório de logs se não existir
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        # File handler - writer.log
        log_file = self.config.log_dir / "writer.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # Error file handler
        error_file = self.config.log_dir / "writer_errors.log"
        error_handler = logging.FileHandler(error_file, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)

        # Formatação
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)

        # Adiciona handlers ao logger do módulo
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)

    def _load_topic_json(self, note_name: str) -> Optional[Dict]:
        """Carrega JSON de tópicos para uma nota."""
        # 1. Try loading from individual JSON file in results/
        json_path = self.config.log_dir / "results" / f"{note_name}_topics.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading JSON for {note_name}: {e}")
                return None

        # 2. Try loading from topic_extractor files (topic_extraction_*.json)
        topics_dir = self.config.log_dir
        result_data = None

        if topics_dir.exists():
            for json_file in sorted(topics_dir.glob("topic_extraction_*.json")):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for result in data.get("results", []):
                            file_path = result.get("file", "")
                            if file_path and Path(file_path).stem == note_name:
                                # Check if this result has actual data (either direct or in 'data' field)
                                if result.get("status") == "success":
                                    # Try direct topics first, then check 'data' field
                                    topics = result.get("topics", [])
                                    cdu_primary = result.get("cdu_primary")
                                    cdu_secondary = result.get("cdu_secondary", [])
                                    cdu_description = result.get("cdu_description")
                                    content_summary = result.get("content_summary")

                                    # If not found directly, check inside 'data' field
                                    if not topics and result.get("data"):
                                        topics = result.get("data", {}).get(
                                            "topics", []
                                        )
                                        cdu_primary = cdu_primary or result.get(
                                            "data", {}
                                        ).get("cdu_primary")
                                        cdu_secondary = cdu_secondary or result.get(
                                            "data", {}
                                        ).get("cdu_secondary", [])
                                        cdu_description = cdu_description or result.get(
                                            "data", {}
                                        ).get("cdu_description")
                                        content_summary = content_summary or result.get(
                                            "data", {}
                                        ).get("content_summary")

                                    if topics:
                                        return {
                                            "topics": topics,
                                            "cdu_primary": cdu_primary,
                                            "cdu_secondary": cdu_secondary,
                                            "cdu_description": cdu_description,
                                            "content_summary": content_summary,
                                        }
                                elif result.get("status") == "dry-run":
                                    # Skip dry-run entries, keep searching
                                    continue
                except Exception as e:
                    logger.debug(f"Error reading {json_file}: {e}")
                    continue

        if result_data:
            return result_data

        # 3. Try loading from pipeline_extraction files
        results_dir = self.config.log_dir / "results"

        if results_dir.exists():
            for json_file in sorted(results_dir.glob("pipeline_extraction_*.json")):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for result in data.get("results", []):
                            file_path = result.get("file", "")
                            if file_path and Path(file_path).stem == note_name:
                                # Keep searching - we want the latest (most complete) data
                                result_data = result.get("data", {})
                                if (
                                    result_data
                                ):  # If we found data, continue to find later entries
                                    break
                except Exception as e:
                    logger.debug(f"Error reading {json_file}: {e}")
                    continue

        if result_data:
            return result_data

        # 4. Also try the test file
        test_file = self.config.log_dir / "test_extraction_5_notes.json"
        if test_file.exists():
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for note in data.get("results", {}).get("notes", []):
                        if note.get("file") == note_name or note.get(
                            "file", ""
                        ).startswith(note_name):
                            return note
            except Exception as e:
                logger.error(f"Error loading from test file: {e}")

        return None

    def _read_note(self, note_path: Path) -> Tuple[Dict, str, str]:
        """Lê nota e separa frontmatter do conteúdo."""
        with open(note_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verifica se tem frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_raw = parts[1]
                content_body = parts[2]
                try:
                    frontmatter_dict = yaml.safe_load(frontmatter_raw) or {}
                except yaml.YAMLError as e:
                    logger.error(f"YAML parse error in {note_path}: {e}")
                    frontmatter_dict = {}
                return frontmatter_dict, content_body, frontmatter_raw

        # Sem frontmatter
        return {}, content, ""

    def _write_note(self, note_path: Path, frontmatter: Dict, content_body: str):
        """Escreve nota com frontmatter atualizado."""
        # Serializa frontmatter para YAML
        frontmatter_yaml = yaml.dump(
            frontmatter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=1000,  # Evita quebra de linha em valores longos
        )

        # Garante que o content_body começa com newline se não estiver vazio
        if content_body and not content_body.startswith("\n"):
            content_body = "\n" + content_body

        # Monta conteúdo completo
        new_content = f"---\n{frontmatter_yaml}---{content_body}"

        # Escreve arquivo
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    def _build_topic_classification(
        self, topic_json: Dict, note_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Constrói estrutura topic_classification para o frontmatter.

        Args:
            topic_json: The extracted topic data from Gemini
            note_path: Path to the note file for fallback CDU inference
        """
        cdu_primary = topic_json.get("cdu_primary")
        cdu_description = topic_json.get("cdu_description")

        # Fallback: infer CDU from folder/keywords if null
        if not cdu_primary and note_path:
            inferred_cdu = infer_cdu_fallback(str(note_path))
            if inferred_cdu:
                cdu_primary = inferred_cdu
                cdu_description = get_cdu_description(inferred_cdu)
                logger.debug(f"   🔄 Fallback CDU for {note_path.name}: {inferred_cdu}")

        return {
            "version": "2.0",
            "classified_at": datetime.now(timezone.utc).isoformat(),
            "model": topic_json.get("model", "gemini-2.5-flash-lite"),
            "topics": topic_json.get("topics", []),
            "cdu_primary": cdu_primary,
            "cdu_secondary": topic_json.get("cdu_secondary", []),
            "cdu_description": cdu_description,
        }

    def write_properties(self, note_path: Path) -> bool:
        """Escreve properties em uma única nota."""
        try:
            note_name = note_path.stem

            # Carrega JSON de tópicos
            topic_json = self._load_topic_json(note_name)
            if not topic_json:
                logger.warning(f"⚠️ No topic JSON for {note_name}. Skipping.")
                self.stats["skipped"] += 1
                return False

            # Lê nota atual
            frontmatter, content_body, _ = self._read_note(note_path)

            # Constrói topic_classification
            topic_classification = self._build_topic_classification(
                topic_json, note_path
            )

            # Atualiza ou adiciona frontmatter
            frontmatter["topic_classification"] = topic_classification

            # Dry-run: apenas log, não escreve
            if self.config.dry_run:
                logger.info(f"📝 [DRY-RUN] Would update: {note_path.name}")
                logger.info(f"   Topics: {len(topic_classification['topics'])}")
                logger.info(f"   CDU: {topic_classification['cdu_primary']}")
                return True

            # Escreve nota atualizada
            self._write_note(note_path, frontmatter, content_body)
            logger.info(
                f"✅ Updated: {note_path.name} - {len(topic_classification['topics'])} topics"
            )
            self.stats["modified"].append(str(note_path))
            return True

        except Exception as e:
            logger.error(f"❌ Error writing {note_path.name}: {e}")
            return False

    def _find_notes_with_jsons(self, vault_dir: Path) -> List[Path]:
        """Encontra notas que têm JSON correspondente."""
        notes = []
        results_dir = self.config.log_dir / "results"

        # Coleta nomes de arquivos JSON disponíveis
        json_names = set()

        # 1. Procura em data/logs/topics/ (arquivos do topic_extractor)
        topics_dir = self.config.log_dir
        if topics_dir.exists():
            for json_file in topics_dir.glob("topic_extraction_*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for result in data.get("results", []):
                            file_path = result.get("file", "")
                            if file_path:
                                json_names.add(Path(file_path).stem)
                except Exception:
                    pass

        # 2. Procura em data/logs/topics/results/ (arquivos do pipeline)
        if results_dir.exists():
            # Look for *_topics.json files
            for json_file in results_dir.glob("*_topics.json"):
                json_names.add(json_file.stem.replace("_topics", ""))

            # Also look for pipeline_extraction_*.json files
            for json_file in results_dir.glob("pipeline_extraction_*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for result in data.get("results", []):
                            file_path = result.get("file", "")
                            if file_path:
                                json_names.add(Path(file_path).stem)
                except Exception:
                    pass

        # Também verifica no arquivo de teste
        test_file = self.config.log_dir / "test_extraction_5_notes.json"
        if test_file.exists():
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for note in data.get("results", {}).get("notes", []):
                        file_name = note.get("file", "")
                        if file_name:
                            json_names.add(Path(file_name).stem)
            except Exception:
                pass

        if not json_names:
            logger.warning("⚠️ No topic JSONs found")
            return []

        # Encontra notas correspondentes no vault
        for md_file in vault_dir.rglob("*.md"):
            if md_file.name.startswith("."):
                continue
            if ".obsidian" in str(md_file):
                continue
            if md_file.stem in json_names:
                notes.append(md_file)

        return notes

    def run(self, vault_dir: Path) -> List[Path]:
        """Executa escrita em múltiplas notas."""
        notes = self._find_notes_with_jsons(vault_dir)

        if not notes:
            logger.warning("⚠️ No notes with topic JSONs found")
            return []

        # Aplica limite se especificado
        if self.config.limit and self.config.limit > 0:
            notes = notes[: self.config.limit]
            logger.info(f"⏱️ Limited to {len(notes)} notes")

        self.stats["total_jsons"] = len(notes)
        logger.info(f"🚀 Starting vault write: {len(notes)} notes")
        logger.info(f"📝 Dry run: {self.config.dry_run}")
        logger.info(f"📁 Vault: {vault_dir}")

        modified = []

        for i, note_path in enumerate(notes, 1):
            logger.info(f"[{i}/{len(notes)}] {note_path.name}")

            if self.write_properties(note_path):
                self.stats["successful"] += 1
                if not self.config.dry_run:
                    modified.append(note_path)
            else:
                self.stats["failed"] += 1

        self._log_stats()
        return modified

    def _log_stats(self):
        """Loga estatísticas finais."""
        logger.info("=" * 60)
        logger.info("📊 VAULT WRITE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total JSONs: {self.stats['total_jsons']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped: {self.stats['skipped']}")

        if self.stats["total_jsons"] > 0:
            success_rate = (self.stats["successful"] / self.stats["total_jsons"]) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")

        # Salva stats em arquivo
        stats_file = self.config.log_dir / "writer_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sprint 09: Vault Properties Writer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run em vault completo
  python -m src.topics.vault_writer --vault-dir "/path/to/vault" --dry-run
  
  # Teste piloto (10 notas)
  python -m src.topics.vault_writer --vault-dir "/path/to/vault" --limit 10
  
  # Modo real (após dry-run validado)
  python -m src.topics.vault_writer --vault-dir "/path/to/vault"
        """,
    )

    parser.add_argument(
        "--vault-dir",
        type=str,
        required=True,
        help="Diretório do vault Obsidian (obrigatório)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Apenas log, não modifica notas"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limitar número de notas para processar"
    )

    args = parser.parse_args()

    # Configura
    config = TopicConfig()
    config.dry_run = args.dry_run
    config.limit = args.limit

    # Cria writer
    writer = VaultWriter(config)

    # Executa
    vault_dir = Path(args.vault_dir)
    modified = writer.run(vault_dir)

    # Código de retorno
    if writer.stats["failed"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
