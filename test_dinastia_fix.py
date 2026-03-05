#!/usr/bin/env python3
"""Test script to re-process Dinastia chapter 1 with fixed vault path."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion.pdf_processor import PDFProcessor


def test_dinastia_chapter_1():
    """Test processing chapter 1 of Dinastia book."""
    print("🚀 Testando processamento do capítulo 1 do livro Dinastia...")
    print("📁 Verificando configurações...")

    # Initialize processor
    processor = PDFProcessor(
        target_language="pt",
        enable_translation=True,
        use_chapter_mode=True,
        chapters_file="data/capitulos.txt",
        book_name="Dinastia",
        force_retranslate=False,  # Use existing translation cache
    )

    print(f"📚 Book name: {processor.book_name}")
    print(f"📁 Vault path: {processor.vault_path}")

    # Check if PDF exists
    pdf_path = Path("/home/s015533607/Documentos/Dinastia.pdf")
    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        return

    print(f"✅ PDF encontrado: {pdf_path}")

    # Process only chapter 1 (dry run first to check)
    print("\n🔍 Executando dry run (verificação)...")
    dry_run_result = processor.process_pdf(pdf_path=pdf_path, dry_run=True)
    print(f"Dry run resultado: {dry_run_result}")

    if dry_run_result.get("success"):
        print("\n🎯 Executando processamento real...")
        result = processor.process_pdf(pdf_path=pdf_path, dry_run=False)
        print(f"✅ Processamento completo!")
        print(f"Capítulos processados: {result.get('chapters', 0)}")

        # Check the generated file
        output_file = Path(
            "/home/s015533607/MEGAsync/Minhas_notas/100 ARQUIVOS E REFERENCIAS/Livros/Dinastia/00_Capitulo_01.md"
        )
        if output_file.exists():
            print(f"\n📄 Arquivo gerado: {output_file}")

            # Check for thematic connections
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()

            if "thematic_connections" in content:
                print("✅ thematic_connections encontrado no frontmatter")
            else:
                print("❌ thematic_connections NÃO encontrado no frontmatter")

            if "Conexões Validadas com o Vault" in content:
                print("✅ Seção 'Conexões Validadas' encontrada")
                # Check if it has wikilinks
                import re

                wikilinks = re.findall(r"\[\[(.*?)\]\]", content)
                if wikilinks:
                    print(f"✅ Wikilinks encontrados: {len(wikilinks)}")
                    for wl in wikilinks[:5]:  # Show first 5
                        print(f"   - [[{wl}]]")
                else:
                    print("❌ Nenhum wikilink encontrado na seção")
            else:
                print("❌ Seção 'Conexões Validadas' NÃO encontrada")
        else:
            print(f"❌ Arquivo não gerado: {output_file}")
    else:
        print("❌ Dry run falhou")


if __name__ == "__main__":
    test_dinastia_chapter_1()
