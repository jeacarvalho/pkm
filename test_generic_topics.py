#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, "/home/s015533607/Documentos/desenv/pkm/src")

from topics.topic_matcher import TopicMatcher
from topics.config import TopicConfig
from utils.config import settings


def main():
    print("=== TESTE COM TEMAS GENÉRICOS ===")
    print(f"Vault path: {settings.vault_path}")

    # Criar TopicConfig e TopicMatcher
    topic_config = TopicConfig()
    matcher = TopicMatcher(topic_config)

    # Temas genéricos que podem existir no vault
    generic_topics = {
        "topics": [
            {"name": "lideranca", "weight": 10, "confidence": 0.98},
            {"name": "gestao", "weight": 9, "confidence": 0.95},
            {"name": "historia", "weight": 8, "confidence": 0.92},
            {"name": "estrategia", "weight": 7, "confidence": 0.9},
            {"name": "comunicacao", "weight": 6, "confidence": 0.88},
        ],
        "cdu_primary": "658",
        "cdu_secondary": ["93", "65"],
        "cdu_description": "Liderança, gestão, história, estratégia e comunicação.",
    }

    print(f"\nBuscando conexões para temas genéricos...")
    print(f"Temas: {[t['name'] for t in generic_topics['topics']]}")

    # Buscar conexões usando match_chapter_to_vault
    connections = matcher.match_chapter_to_vault(
        generic_topics["topics"],
        vault_dir=Path(settings.vault_path),
        top_k=10,  # Buscar mais conexões
        threshold=5.0,  # Threshold mais baixo
    )

    print(f"\n=== RESULTADOS ===")
    print(f"Total de conexões encontradas: {len(connections)}")

    if connections:
        print("\nTop 10 conexões:")
        for i, conn in enumerate(connections[:10], 1):
            print(f"{i}. {conn.get('note_title', 'N/A')}")
            print(f"   Score: {conn.get('score', 0):.2f}")
            print(f"   Path: {conn.get('note_path', 'N/A')}")
            matched = conn.get("matched_topics", [])
            if matched:
                print(
                    f"   Temas correspondentes: {[m['chapter_topic'] for m in matched[:3]]}"
                )
            print()
    else:
        print("Nenhuma conexão encontrada!")

        # Verificar notas específicas do usuário
        print("\n=== VERIFICANDO NOTAS ESPECÍFICAS ===")
        specific_notes = [
            "/home/s015533607/MEGAsync/Minhas_notas/30 LIDERANCA/10 grandes TED Talks para líderes.md",
            "/home/s015533607/MEGAsync/Minhas_notas/30 LIDERANCA/coordenar significa fazer com que as pessoas certas estejam nos lugares certos para executar a função correta.md",
            "/home/s015533607/MEGAsync/Minhas_notas/30 LIDERANCA/Lacuna de alinhamento.md",
        ]

        for note_path in specific_notes:
            if Path(note_path).exists():
                frontmatter = matcher._read_note_frontmatter(Path(note_path))
                if frontmatter:
                    print(f"\nNota: {Path(note_path).name}")
                    if "topic_classification" in frontmatter:
                        topics = frontmatter["topic_classification"].get("topics", [])
                        print(f"  Temas: {[t.get('name', 'N/A') for t in topics]}")
                        print(
                            f"  CDU: {frontmatter['topic_classification'].get('cdu_primary', 'N/A')}"
                        )
                    else:
                        print("  SEM topic_classification no frontmatter!")
                else:
                    print(f"  Não consegui ler frontmatter")
            else:
                print(f"  Arquivo não encontrado: {note_path}")


if __name__ == "__main__":
    main()
