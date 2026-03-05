#!/usr/bin/env python3
"""Update thematic connections in existing chapter file with new threshold."""

import sys
import json
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.topics.topic_matcher import TopicMatcher
from src.topics.config import TopicConfig


def update_chapter_connections():
    """Update thematic connections in chapter file."""

    chapter_file = Path(
        "/home/s015533607/MEGAsync/Minhas_notas/100 ARQUIVOS E REFERENCIAS/Livros/Dinastia/00_Capitulo_01.md"
    )

    if not chapter_file.exists():
        print(f"Chapter file not found: {chapter_file}")
        return

    print(f"📄 Reading chapter file: {chapter_file}")

    # Read the file
    with open(chapter_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract frontmatter
    if not content.startswith("---"):
        print("❌ No frontmatter found")
        return

    parts = content.split("---", 2)
    if len(parts) < 3:
        print("❌ Malformed frontmatter")
        return

    frontmatter_str = parts[1]
    frontmatter = yaml.safe_load(frontmatter_str)

    # Extract topics from frontmatter
    topic_classification = frontmatter.get("topic_classification", {})
    topics = topic_classification.get("topics", [])

    if not topics:
        print("❌ No topics found in frontmatter")
        return

    print(f"📊 Found {len(topics)} topics in chapter")

    # Create topic matcher
    config = TopicConfig()
    matcher = TopicMatcher(config)

    # Create temporary JSON file with chapter topics
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        chapter_data = {
            "chapter_title": frontmatter.get("chapter_title", "Chapter 1"),
            "topics": topics,
        }
        json.dump(chapter_data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name

    # Calculate chapter relative path for self-match filtering
    vault_root = "/home/s015533607/MEGAsync/Minhas_notas/"
    chapter_file_str = str(chapter_file)
    if chapter_file_str.startswith(vault_root):
        chapter_rel_path = chapter_file_str[len(vault_root) :]
        if chapter_rel_path.endswith(".md"):
            chapter_rel_path = chapter_rel_path[:-3]
    else:
        chapter_rel_path = ""

    try:
        # Run topic matching with threshold=0.0 to see all matches
        print("\n🔍 Running topic matching with threshold=0.0...")
        result = matcher.run(
            chapter_topics_path=Path(tmp_path),
            vault_dir=Path("/home/s015533607/MEGAsync/Minhas_notas"),
            output_path=None,
            top_k=5,
            threshold=0.0,
        )

        matches = result.get("matches", [])
        print(f"✅ Found {len(matches)} matches")

        if matches:
            print("\n🏆 Top matches:")
            for i, match in enumerate(matches, 1):
                note_path = match.get("note_path", "N/A")
                score = match.get("score", 0)
                # Convert absolute path to wikilink
                if note_path.startswith("/home/s015533607/MEGAsync/Minhas_notas/"):
                    rel_path = note_path[
                        len("/home/s015533607/MEGAsync/Minhas_notas/") :
                    ]
                    if rel_path.endswith(".md"):
                        rel_path = rel_path[:-3]
                    print(f"{i}. [[{rel_path}]] - Score: {score:.2f}")
                else:
                    print(f"{i}. {note_path} - Score: {score:.2f}")

            # Update frontmatter with thematic_connections
            thematic_connections = []
            for match in matches:
                note_path = match.get("note_path", "")
                if note_path.startswith("/home/s015533607/MEGAsync/Minhas_notas/"):
                    rel_path = note_path[
                        len("/home/s015533607/MEGAsync/Minhas_notas/") :
                    ]
                    if rel_path.endswith(".md"):
                        rel_path = rel_path[:-3]

                    # Skip self-match (chapter matching with itself)
                    if rel_path == chapter_rel_path:
                        print(f"⚠️  Skipping self-match: {rel_path}")
                        continue

                    thematic_connections.append(
                        {
                            "note": rel_path,
                            "score": match.get("score", 0),
                            "matched_topics": match.get("matched_topics", []),
                        }
                    )

            frontmatter["thematic_connections"] = thematic_connections

            # Update the content
            new_frontmatter_str = yaml.dump(
                frontmatter, allow_unicode=True, default_flow_style=False
            )
            new_content = f"---\n{new_frontmatter_str}---{parts[2]}"

            # Update the "Conexões Validadas" section
            if "## Conexões Validadas com o Vault (Top 5)" in new_content:
                # Find the section
                lines = new_content.split("\n")
                for i, line in enumerate(lines):
                    if "## Conexões Validadas com o Vault (Top 5)" in line:
                        # Replace the section
                        section_start = i
                        # Find the end of the section (next --- or end of file)
                        for j in range(i + 1, len(lines)):
                            if lines[j].startswith("---") and j > i + 2:
                                section_end = j
                                break
                        else:
                            section_end = len(lines)

                        # Create new section
                        new_section = ["## Conexões Validadas com o Vault (Top 5)", ""]

                        if thematic_connections:
                            for conn in thematic_connections:
                                note_name = conn["note"]
                                score = conn["score"]
                                new_section.append(
                                    f"- [[{note_name}]] (score: {score:.2f})"
                                )
                        else:
                            new_section.append(
                                "*Nenhuma conexão temática encontrada para este capítulo*"
                            )

                        new_section.append("")
                        new_section.append("---")

                        # Replace the section
                        lines[section_start:section_end] = new_section
                        new_content = "\n".join(lines)
                        break

            # Write the updated file
            backup_file = chapter_file.with_suffix(".md.backup")
            print(f"\n💾 Creating backup: {backup_file}")
            chapter_file.rename(backup_file)

            print(f"📝 Writing updated file: {chapter_file}")
            with open(chapter_file, "w", encoding="utf-8") as f:
                f.write(new_content)

            print("\n✅ Chapter file updated successfully!")
            print(f"📊 Added {len(thematic_connections)} thematic connections")

        else:
            print("❌ No matches found")

    finally:
        # Clean up temp file
        Path(tmp_path).unlink()


if __name__ == "__main__":
    update_chapter_connections()
