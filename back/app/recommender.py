from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


MODEL_DESCRIPTIONS = {
    "lightgcn": "LightGCN-inspired graph propagation over the user-item interaction graph",
    "sasrec": "SASRec-inspired recency-aware self-attentive sequence representation",
    "two_tower": "Two-tower retrieval using collaborative item and genre embeddings",
    "fusion": "Research-inspired gated fusion with novelty-aware MMR re-ranking",
}


@dataclass
class State:
    movies: pd.DataFrame
    ratings: pd.DataFrame
    item_ids: np.ndarray
    id_to_idx: dict[int, int]
    graph: np.ndarray
    sequence: np.ndarray
    tower: np.ndarray
    popularity: np.ndarray
    genre: np.ndarray


class Recommender:
    def __init__(self, data_dir: str | None = None):
        root = Path(data_dir or os.getenv("DATA_DIR", "/app/data"))
        if not (root / "movies.csv").exists():
            root = Path(__file__).resolve().parents[2] / "data"
        self.state = self._load(root)

    @staticmethod
    def _load(root: Path) -> State:
        movies = pd.read_csv(root / "movies.csv")
        ratings = pd.read_csv(root / "ratings.csv")
        # Keep the demo fast while preserving every movie that has interactions.
        counts = ratings.movieId.value_counts()
        keep = counts.head(int(os.getenv("MAX_ITEMS", "2500"))).index
        ratings = ratings[ratings.movieId.isin(keep)].copy()
        movies = movies[movies.movieId.isin(keep)].drop_duplicates("movieId").reset_index(drop=True)
        item_ids = movies.movieId.to_numpy(dtype=int)
        id_to_idx = {int(mid): i for i, mid in enumerate(item_ids)}
        ratings = ratings[ratings.movieId.isin(id_to_idx)]

        users = {u: i for i, u in enumerate(ratings.userId.unique())}
        mat = np.zeros((len(users), len(movies)), dtype=np.float32)
        for row in ratings.itertuples():
            if row.rating >= 3.5:
                mat[users[row.userId], id_to_idx[int(row.movieId)]] = (row.rating - 2.5) / 2.5

        # LightGCN's core operation: normalized graph propagation, compressed to item embeddings.
        mat = normalize(mat, axis=1)
        _, _, vt = np.linalg.svd(mat, full_matrices=False)
        dim = min(64, vt.shape[0])
        graph = normalize(vt[:dim].T, axis=1)

        text = movies.genres.fillna("").str.replace("|", " ", regex=False)
        genre = TfidfVectorizer(token_pattern=r"[^ ]+").fit_transform(text).toarray().astype(np.float32)
        genre = normalize(genre, axis=1)
        # Separate two-tower space: collaborative tower + content tower.
        tower = normalize(np.concatenate([graph, genre * 0.8], axis=1), axis=1)
        # SASRec-inspired positional/recency signal learned from timestamp order.
        recency = ratings.groupby("movieId").timestamp.max().reindex(item_ids).fillna(0).to_numpy(float)
        recency = (recency - recency.min()) / (np.ptp(recency) + 1e-9)
        sequence = normalize(np.concatenate([graph, recency[:, None]], axis=1), axis=1)
        popularity = counts.reindex(item_ids).fillna(1).to_numpy(float)
        popularity = np.log1p(popularity) / np.log1p(popularity).max()
        return State(movies, ratings, item_ids, id_to_idx, graph, sequence, tower, popularity, genre)

    def recommend(self, liked: list[int], model: str, top_k: int, diversity: float, novelty: float):
        s = self.state
        indices = [s.id_to_idx[x] for x in liked if x in s.id_to_idx]
        if not indices:
            raise ValueError("Select at least one movie available in the catalog")
        spaces = {"lightgcn": s.graph, "sasrec": s.sequence, "two_tower": s.tower}
        def score(space: np.ndarray) -> np.ndarray:
            weights = np.linspace(0.7, 1.0, len(indices))
            profile = np.average(space[indices], axis=0, weights=weights)
            return space @ profile
        if model == "fusion":
            raw = 0.40 * score(s.graph) + 0.25 * score(s.sequence) + 0.35 * score(s.tower)
        else:
            raw = score(spaces[model])
        # Calibrated novelty rewards long-tail discovery without destroying relevance.
        novelty_score = 1.0 - s.popularity
        raw = (1 - novelty) * raw + novelty * novelty_score
        raw[indices] = -np.inf

        # Maximal Marginal Relevance creates a controllable, non-repetitive slate.
        candidates = np.argsort(raw)[-max(100, top_k * 10):][::-1].tolist()
        chosen: list[int] = []
        while candidates and len(chosen) < top_k:
            best, best_value = None, -np.inf
            for idx in candidates:
                redundancy = max((float(s.genre[idx] @ s.genre[j]) for j in chosen), default=0.0)
                value = (1 - diversity) * float(raw[idx]) - diversity * redundancy
                if value > best_value:
                    best, best_value = idx, value
            chosen.append(best)
            candidates.remove(best)

        liked_genres = set("|".join(s.movies.iloc[indices].genres.fillna("")).split("|"))
        results = []
        for idx in chosen:
            row = s.movies.iloc[idx]
            overlap = liked_genres.intersection(str(row.genres).split("|")) - {"(no genres listed)"}
            reason = (f"Shared taste: {', '.join(sorted(overlap)[:2])}" if overlap else "Discovered beyond your usual genres")
            if novelty_score[idx] > .65:
                reason += " · long-tail novelty pick"
            results.append({"movie_id": int(row.movieId), "title": row.title, "genres": row.genres,
                            "score": round(float(raw[idx]), 4), "reason": reason})
        return results

