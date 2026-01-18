"""
ResponseCache - семантическое кэширование ответов на базе ChromaDB.

Использует embedding-based similarity для поиска похожих вопросов.
При similarity >= threshold возвращает закэшированный ответ.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import chromadb
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


@dataclass
class CacheHit:
    """Результат попадания в кэш."""
    question: str
    answer: str
    similarity: float
    intents: list[str]
    confidence: float
    sources: list[dict[str, Any]]
    hits: int
    created_at: str


@dataclass
class CacheMetadata:
    """Метаданные для сохранения в кэш."""
    intents: list[str]
    confidence: float
    sources: list[dict[str, Any]]


@dataclass
class CacheStats:
    """Статистика кэша."""
    enabled: bool
    collection: str
    total_entries: int
    total_hits: int


class ResponseCache:
    """
    Семантический кэш ответов на базе ChromaDB.

    Принцип работы:
    1. При get() - вычисляем embedding вопроса
    2. Ищем в коллекции документы с distance < (1 - threshold)
    3. Если найден - возвращаем CacheHit
    4. При set() - сохраняем вопрос, ответ и metadata
    """

    def __init__(
        self,
        chroma_client: chromadb.HttpClient,
        collection_name: str,
        embeddings: OpenAIEmbeddings,
        similarity_threshold: float = 0.95,
    ):
        """
        Инициализация кэша.

        Args:
            chroma_client: Клиент ChromaDB
            collection_name: Имя коллекции для кэша
            embeddings: Embeddings функция (OpenAI/TEI)
            similarity_threshold: Порог схожести (0.95 = distance < 0.05)
        """
        self._client = chroma_client
        self._collection_name = collection_name
        self._embeddings = embeddings
        self._similarity_threshold = similarity_threshold

        # Distance threshold: ChromaDB uses L2/cosine distance
        # similarity = 1 - distance, so distance = 1 - similarity
        self._distance_threshold = 1.0 - similarity_threshold

        # Получаем или создаём коллекцию
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Response cache for RAG agent"}
        )

        logger.info(
            "ResponseCache initialized: collection=%s, threshold=%.2f, entries=%d",
            collection_name,
            similarity_threshold,
            self._collection.count(),
        )

    def _compute_embedding(self, text: str) -> list[float]:
        """Вычислить embedding для текста."""
        return self._embeddings.embed_query(text)

    def _generate_id(self, question: str) -> str:
        """Генерировать уникальный ID для вопроса."""
        return hashlib.sha256(question.lower().strip().encode()).hexdigest()[:16]

    def get(self, question: str) -> CacheHit | None:
        """
        Поиск похожего вопроса в кэше.

        Args:
            question: Вопрос пользователя

        Returns:
            CacheHit если найден похожий вопрос, иначе None
        """
        if not question or not question.strip():
            return None

        try:
            # Вычисляем embedding
            query_embedding = self._compute_embedding(question)

            # Ищем похожие
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=1,
                include=["documents", "metadatas", "distances"],
            )

            # Проверяем результат
            if not results["ids"] or not results["ids"][0]:
                return None

            distances = results["distances"][0] if results["distances"] else []
            if not distances:
                return None

            distance = distances[0]

            # Проверяем порог
            if distance > self._distance_threshold:
                logger.debug(
                    "Cache MISS: distance=%.4f > threshold=%.4f",
                    distance,
                    self._distance_threshold,
                )
                return None

            # Попадание в кэш
            metadata = results["metadatas"][0][0] if results["metadatas"] else {}
            original_question = results["documents"][0][0] if results["documents"] else ""

            similarity = 1.0 - distance

            # Инкрементируем счётчик hits
            doc_id = results["ids"][0][0]
            self._increment_hits(doc_id, metadata)

            logger.info(
                "Cache HIT: similarity=%.4f, original_q=%r",
                similarity,
                original_question[:50],
            )

            # Парсим sources из JSON строки
            sources_raw = metadata.get("sources", "[]")
            if isinstance(sources_raw, str):
                import json
                try:
                    sources = json.loads(sources_raw)
                except json.JSONDecodeError:
                    sources = []
            else:
                sources = sources_raw if isinstance(sources_raw, list) else []

            # Парсим intents
            intents_raw = metadata.get("intents", "[]")
            if isinstance(intents_raw, str):
                import json
                try:
                    intents = json.loads(intents_raw)
                except json.JSONDecodeError:
                    intents = []
            else:
                intents = intents_raw if isinstance(intents_raw, list) else []

            return CacheHit(
                question=original_question,
                answer=metadata.get("answer", ""),
                similarity=similarity,
                intents=intents,
                confidence=float(metadata.get("confidence", 0.0)),
                sources=sources,
                hits=int(metadata.get("hits", 0)) + 1,
                created_at=metadata.get("created_at", ""),
            )

        except Exception as e:
            logger.warning("Cache get failed: %s", e)
            return None

    def _increment_hits(self, doc_id: str, metadata: dict[str, Any]) -> None:
        """Инкрементировать счётчик hits для документа."""
        try:
            current_hits = int(metadata.get("hits", 0))
            metadata["hits"] = current_hits + 1
            self._collection.update(
                ids=[doc_id],
                metadatas=[metadata],
            )
        except Exception as e:
            logger.warning("Failed to increment hits: %s", e)

    def set(
        self,
        question: str,
        answer: str,
        metadata: CacheMetadata,
    ) -> bool:
        """
        Сохранить ответ в кэш.

        Args:
            question: Вопрос пользователя
            answer: Сгенерированный ответ
            metadata: Дополнительные метаданные

        Returns:
            True если успешно сохранено
        """
        if not question or not answer:
            return False

        try:
            import json

            doc_id = self._generate_id(question)
            embedding = self._compute_embedding(question)

            # Подготавливаем metadata для ChromaDB
            # ChromaDB требует примитивные типы в metadata
            chroma_metadata = {
                "answer": answer,
                "intents": json.dumps(metadata.intents),
                "confidence": metadata.confidence,
                "sources": json.dumps(metadata.sources),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "hits": 0,
            }

            # Upsert - обновляем если существует
            self._collection.upsert(
                ids=[doc_id],
                documents=[question],
                embeddings=[embedding],
                metadatas=[chroma_metadata],
            )

            logger.info(
                "Cache SET: id=%s, question=%r, intents=%s",
                doc_id,
                question[:50],
                metadata.intents,
            )

            return True

        except Exception as e:
            logger.warning("Cache set failed: %s", e)
            return False

    def clear(self) -> int:
        """
        Очистить весь кэш.

        Returns:
            Количество удалённых записей
        """
        try:
            count = self._collection.count()

            # Удаляем и пересоздаём коллекцию
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"description": "Response cache for RAG agent"}
            )

            logger.info("Cache cleared: %d entries removed", count)
            return count

        except Exception as e:
            logger.warning("Cache clear failed: %s", e)
            return 0

    def stats(self) -> CacheStats:
        """
        Получить статистику кэша.

        Returns:
            CacheStats с информацией о кэше
        """
        try:
            total = self._collection.count()

            # Подсчитываем общее количество hits
            total_hits = 0
            if total > 0:
                data = self._collection.get(include=["metadatas"])
                for md in data.get("metadatas") or []:
                    if md:
                        total_hits += int(md.get("hits", 0))

            return CacheStats(
                enabled=True,
                collection=self._collection_name,
                total_entries=total,
                total_hits=total_hits,
            )

        except Exception as e:
            logger.warning("Cache stats failed: %s", e)
            return CacheStats(
                enabled=True,
                collection=self._collection_name,
                total_entries=0,
                total_hits=0,
            )
