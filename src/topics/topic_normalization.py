#!/usr/bin/env python3
"""
Topic normalization - map specific topics to broader categories
"""

import re
from typing import List, Dict, Tuple


class TopicNormalizer:
    """Normalizes specific topics to broader categories"""

    def __init__(self):
        # Mapping from specific topics to broader categories
        self.normalization_map = {
            # Roman history topics → broader categories
            "figura_de_augusto_como_princeps": ["lideranca", "poder", "governanca"],
            "reconciliacao_passado_futuro_roma": ["mudanca", "transicao", "adaptacao"],
            "paz_restaurada_por_augusto": ["paz", "estabilidade", "seguranca"],
            "relacao_augusto_com_os_deuses": ["religiao", "crencas", "espiritualidade"],
            "horacio_e_o_veredicto_sobre_augusto": [
                "critica",
                "avaliacao",
                "julgamento",
            ],
            "expansao_militar_romana_e_britania": [
                "expansao",
                "conquista",
                "imperialismo",
            ],
            "fundacao_de_roma_e_dominio_global": ["fundacao", "origem", "dominio"],
            # General patterns
            r".*augusto.*": ["lideranca", "poder"],
            r".*roma.*": ["civilizacao", "historia", "imperio"],
            r".*militar.*": ["guerra", "conflito", "estrategia"],
            r".*expansao.*": ["crescimento", "expansao", "conquista"],
            r".*fundacao.*": ["origem", "criacao", "inicio"],
            r".*paz.*": ["paz", "harmonia", "estabilidade"],
            r".*deuses.*": ["religiao", "divindade", "crencas"],
            r".*veredicto.*": ["julgamento", "avaliacao", "critica"],
            r".*reconciliacao.*": ["reconciliacao", "uniao", "harmonia"],
            # Broader historical concepts
            "imperio": ["poder", "dominio", "governanca"],
            "conquista": ["expansao", "poder", "dominio"],
            "civilizacao": ["sociedade", "cultura", "desenvolvimento"],
            "historia": ["passado", "tradicao", "legado"],
        }

        # Broader categories that might match vault topics
        self.broad_categories = [
            "lideranca",
            "poder",
            "governanca",
            "mudanca",
            "transicao",
            "adaptacao",
            "paz",
            "estabilidade",
            "seguranca",
            "religiao",
            "crencas",
            "espiritualidade",
            "critica",
            "avaliacao",
            "julgamento",
            "expansao",
            "conquista",
            "imperialismo",
            "fundacao",
            "origem",
            "dominio",
            "guerra",
            "conflito",
            "estrategia",
            "crescimento",
            "civilizacao",
            "sociedade",
            "cultura",
            "desenvolvimento",
            "historia",
            "passado",
            "tradicao",
            "legado",
            "reconciliacao",
            "uniao",
            "harmonia",
        ]

    def normalize_topic(self, topic_name: str) -> List[str]:
        """Normalize a specific topic to broader categories"""
        normalized = []

        # Check exact matches first
        if topic_name in self.normalization_map:
            normalized.extend(self.normalization_map[topic_name])

        # Check pattern matches
        for pattern, categories in self.normalization_map.items():
            if pattern.startswith(".*") and pattern.endswith(".*"):
                if re.search(pattern, topic_name, re.IGNORECASE):
                    normalized.extend(categories)

        # Add some generic categories based on common words
        topic_lower = topic_name.lower()
        if any(word in topic_lower for word in ["lider", "chefe", "governo", "poder"]):
            normalized.extend(["lideranca", "poder", "governanca"])
        if any(word in topic_lower for word in ["mudanc", "transic", "adapt"]):
            normalized.extend(["mudanca", "transicao", "adaptacao"])
        if any(word in topic_lower for word in ["paz", "harmonia", "estabilidade"]):
            normalized.extend(["paz", "harmonia", "estabilidade"])
        if any(
            word in topic_lower for word in ["deus", "divino", "religiao", "crenca"]
        ):
            normalized.extend(["religiao", "espiritualidade", "crencas"])

        # Remove duplicates and return
        return list(set(normalized))

    def normalize_topics(self, topics: List[Dict]) -> List[Dict]:
        """Normalize a list of topics"""
        normalized_topics = []

        for topic in topics:
            topic_name = topic.get("name", "")
            original_weight = topic.get("weight", 5)
            original_confidence = topic.get("confidence", 0)

            # Get normalized categories
            normalized_categories = self.normalize_topic(topic_name)

            # Add original topic (with reduced weight)
            if normalized_categories:
                # Reduce weight of original since we'll add normalized versions
                normalized_topics.append(
                    {
                        "name": topic_name,
                        "weight": max(1, original_weight // 2),  # Reduce weight
                        "confidence": original_confidence,
                        "is_original": True,
                    }
                )

                # Add normalized categories (with reduced weight)
                for category in normalized_categories:
                    normalized_topics.append(
                        {
                            "name": category,
                            "weight": max(2, original_weight // 3),  # Even lower weight
                            "confidence": original_confidence
                            * 0.8,  # Reduced confidence
                            "is_normalized": True,
                            "original_topic": topic_name,
                        }
                    )
            else:
                # Keep original if no normalization
                normalized_topics.append(topic)

        return normalized_topics

    def test_normalization(self):
        """Test the normalization with chapter topics"""
        chapter_topics = [
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
        ]

        print("Original topics:")
        for topic in chapter_topics:
            print(f"  - {topic['name']} (weight: {topic['weight']})")

        normalized = self.normalize_topics(chapter_topics)

        print("\nNormalized topics:")
        for topic in normalized:
            is_orig = topic.get("is_original", False)
            is_norm = topic.get("is_normalized", False)
            orig = topic.get("original_topic", "")

            if is_orig:
                print(f"  - {topic['name']} (weight: {topic['weight']}) [ORIGINAL]")
            elif is_norm:
                print(
                    f"  - {topic['name']} (weight: {topic['weight']}) [NORMALIZED from: {orig}]"
                )
            else:
                print(f"  - {topic['name']} (weight: {topic['weight']})")


if __name__ == "__main__":
    normalizer = TopicNormalizer()
    normalizer.test_normalization()
