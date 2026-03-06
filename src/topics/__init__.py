"""Topics extraction module for Obsidian RAG."""

from src.topics.config import TopicConfig, topics_config
from src.topics.topic_extractor import TopicExtractor
from src.topics.topic_validator import TopicValidator, TopicValidationError
from src.topics.taxonomy_manager import CDUManager
from src.topics.topic_normalization import TopicNormalizer

__all__ = [
    "TopicConfig",
    "topics_config",
    "TopicExtractor",
    "TopicValidator",
    "TopicValidationError",
    "CDUManager",
    "TopicNormalizer",
]
