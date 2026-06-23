"""BERTopic theme discovery with a deterministic small-dataset fallback."""

from __future__ import annotations

from collections import Counter

import numpy as np


class ThemeDiscoveryPipeline:
    def __init__(self, n_themes: int = 8, min_topic_size: int = 5, language: str = "english"):
        self.n_themes = n_themes
        self.min_topic_size = min_topic_size
        self.language = language
        self.model = None
        self._themes: dict[int, dict] = {}

    def fit_transform(self, texts: list[str], embeddings: np.ndarray) -> tuple[list[int], list[float]]:
        # BERTopic/HDBSCAN needs a meaningful corpus. A compact deterministic fallback
        # keeps demos and tests useful without pretending tiny samples are robust topics.
        if len(texts) < max(10, self.min_topic_size * 2):
            from sklearn.cluster import KMeans
            from sklearn.feature_extraction.text import TfidfVectorizer

            clusters = min(self.n_themes, max(1, len(texts) // 3))
            labels = KMeans(n_clusters=clusters, random_state=42, n_init=10).fit_predict(embeddings).tolist()
            vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
            terms = vectorizer.fit_transform(texts)
            vocab = np.asarray(vectorizer.get_feature_names_out())
            for topic_id in sorted(set(labels)):
                indexes = [i for i, label in enumerate(labels) if label == topic_id]
                weights = np.asarray(terms[indexes].mean(axis=0)).ravel()
                keywords = vocab[weights.argsort()[::-1][:10]].tolist()
                self._themes[topic_id] = self._theme(topic_id, keywords)
            return labels, [1.0] * len(labels)

        from bertopic import BERTopic

        self.model = BERTopic(
            nr_topics=self.n_themes,
            min_topic_size=self.min_topic_size,
            language=self.language,
            calculate_probabilities=True,
            verbose=False,
        )
        topics, probs = self.model.fit_transform(texts, embeddings)
        if probs is None:
            probabilities = [1.0] * len(topics)
        else:
            probabilities = probs.max(axis=1).tolist() if getattr(probs, "ndim", 1) > 1 else np.asarray(probs).tolist()
        for topic_id in sorted(set(topics)):
            words = self.model.get_topic(topic_id) or []
            keywords = [word for word, _ in words[:10]] or ["other"]
            self._themes[topic_id] = self._theme(topic_id, keywords)
        return list(map(int, topics)), list(map(float, probabilities))

    @staticmethod
    def _theme(topic_id: int, keywords: list[str]) -> dict:
        clean = [word.replace("_", " ").title() for word in keywords[:3]]
        name = " / ".join(clean) if topic_id != -1 else "Other"
        return {"id": topic_id, "name": name, "keywords": keywords}

    def get_themes(self) -> dict[int, dict]:
        return self._themes
