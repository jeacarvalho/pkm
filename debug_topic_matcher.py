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
    print("=== DEBUG TOPIC MATCHER ===")
    print(f"Vault path: {settings.vault_path}")

    # Criar TopicConfig e TopicMatcher
    topic_config = TopicConfig()
    matcher = TopicMatcher(topic_config)

    # Temas do capítulo 1 do Dinastia
    chapter_topics = {
        "topics": [
            {
                "name": "figura_de_augusto_como_princeps",
                "weight": 10,
                "confidence": 0.98,
            },
            {
                "name": "reconciliacao_passado_futuro_roma",
                "weight": 9,
                "confidence": 0.95,
            },
            {"name": "paz_restaurada_por_augusto", "weight": 8, "confidence": 0.92},
            {"name": "relacao_augusto_com_os_deuses", "weight": 7, "confidence": 0.9},
            {
                "name": "horacio_e_o_veredicto_sobre_augusto",
                "weight": 6,
                "confidence": 0.88,
            },
            {
                "name": "agradecimentos_a_editores_e_colaboradores",
                "weight": 5,
                "confidence": 0.85,
            },
            {"name": "dedicatoria_do_livro_a_katy", "weight": 5, "confidence": 0.8},
            {
                "name": "cenario_do_prefacio_imperador_caio_germanico",
                "weight": 7,
                "confidence": 0.93,
            },
            {
                "name": "expansao_militar_romana_e_britania",
                "weight": 8,
                "confidence": 0.94,
            },
            {
                "name": "fundacao_de_roma_e_dominio_global",
                "weight": 9,
                "confidence": 0.96,
            },
        ],
        "cdu_primary": "937",
        "cdu_secondary": ["940", "930.2"],
        "cdu_description": "História da Roma Antiga, com ênfase no período imperial, expansão e figuras chave como Augusto. Inclui também elementos de história militar e social.",
    }

    print(
        f"\nBuscando conexões para capítulo com {len(chapter_topics['topics'])} temas..."
    )
    print(f"CDU primário: {chapter_topics['cdu_primary']}")
    print(f"CDU secundário: {chapter_topics['cdu_secondary']}")

    # Buscar conexões usando match_chapter_to_vault
    connections = matcher.match_chapter_to_vault(
        chapter_topics["topics"],
        vault_dir=Path(settings.vault_path),
        top_k=5,
        threshold=10.0,
    )

    print(f"\n=== RESULTADOS ===")
    print(f"Total de conexões encontradas: {len(connections)}")

    if connections:
        print("\nTop 5 conexões:")
        for i, conn in enumerate(connections[:5], 1):
            print(f"{i}. {conn.get('note_title', 'N/A')}")
            print(f"   Score: {conn.get('score', 0):.2f}")
            print(f"   Path: {conn.get('note_path', 'N/A')}")
            print(f"   Matched topics: {conn.get('matched_topics', [])}")
            print()
    else:
        print("Nenhuma conexão encontrada!")

        # Verificar quantas notas têm topic_classification
        print("\n=== VERIFICAÇÃO DO VAULT ===")
        notes = matcher._find_notes_with_topics(Path(settings.vault_path))
        print(f"Total de notas .md no vault: {len(notes)}")

        # Verificar quantas têm topic_classification
        notes_with_topics = []
        for note_path in notes[:20]:  # Verificar apenas as primeiras 20
            frontmatter = matcher._read_note_frontmatter(note_path)
            if frontmatter and "topic_classification" in frontmatter:
                notes_with_topics.append(
                    {
                        "path": note_path,
                        "title": frontmatter.get("title", note_path.name),
                        "topics": frontmatter["topic_classification"].get("topics", []),
                    }
                )

        print(
            f"Notas com topic_classification (nas primeiras 20): {len(notes_with_topics)}"
        )

        if notes_with_topics:
            print("\nPrimeiras 5 notas com topic_classification:")
            for i, note in enumerate(notes_with_topics[:5], 1):
                print(f"{i}. {note['title']}")
                print(f"   Path: {note['path']}")
                print(f"   Temas: {len(note['topics'])}")
                if note["topics"]:
                    print(f"   Primeiro tema: {note['topics'][0].get('name', 'N/A')}")
                print()


if __name__ == "__main__":
    main()
