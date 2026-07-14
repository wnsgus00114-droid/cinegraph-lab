"""MovieLens로 개인화 MLP 평점 예측 모델을 학습하고 배포 산출물을 생성한다."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "artifacts" / "mlp_recommender.joblib"
METADATA = ROOT / "artifacts" / "mlp_metrics.json"


def main() -> None:
    movies = pd.read_csv(DATA / "movies.csv")
    ratings = pd.read_csv(DATA / "ratings.csv")
    counts = ratings.movieId.value_counts()
    keep = counts.head(2500).index
    movies = movies[movies.movieId.isin(keep)].drop_duplicates("movieId").reset_index(drop=True)
    ratings = ratings[ratings.movieId.isin(keep)].copy()

    vectorizer = TfidfVectorizer(token_pattern=r"[^ ]+")
    genres = normalize(vectorizer.fit_transform(
        movies.genres.fillna("").str.replace("|", " ", regex=False)
    ).toarray().astype(np.float32), axis=1)
    id_to_idx = {int(mid): i for i, mid in enumerate(movies.movieId)}

    # 각 사용자가 높은 평점을 준 영화의 장르로 선호 프로필을 구성한다.
    profiles: dict[int, np.ndarray] = {}
    for user_id, group in ratings.groupby("userId"):
        idx = [id_to_idx[int(mid)] for mid in group.movieId]
        weights = np.maximum(group.rating.to_numpy(dtype=float) - 2.5, 0.1)
        profiles[int(user_id)] = np.average(genres[idx], axis=0, weights=weights).astype(np.float32)

    # CI와 t3.micro에서도 재현 가능하도록 고정 시드로 학습 표본을 추출한다.
    sample = ratings.sample(n=min(40000, len(ratings)), random_state=42)
    movie_idx = np.array([id_to_idx[int(mid)] for mid in sample.movieId])
    user_features = np.stack([profiles[int(uid)] for uid in sample.userId])
    movie_features = genres[movie_idx]
    popularity = np.log1p(counts.reindex(sample.movieId).to_numpy(float)) / np.log1p(counts.max())
    x = np.concatenate([user_features, movie_features, user_features * movie_features,
                        popularity[:, None]], axis=1)
    y = sample.rating.to_numpy(dtype=np.float32)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    model = MLPRegressor(hidden_layer_sizes=(64, 32), activation="relu", solver="adam",
                         alpha=0.0005, batch_size=256, learning_rate_init=0.001,
                         max_iter=35, early_stopping=True, random_state=42)
    model.fit(x_train, y_train)
    prediction = model.predict(x_test)
    metrics = {
        "model": "MLPRegressor(64,32)",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "samples": int(len(sample)),
        "features": int(x.shape[1]),
        "epochs": int(model.n_iter_),
        "rmse": round(float(root_mean_squared_error(y_test, prediction)), 4),
        "mae": round(float(mean_absolute_error(y_test, prediction)), 4),
        "random_seed": 42,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "metrics": metrics,
                 "genre_vocabulary": vectorizer.get_feature_names_out().tolist()}, OUTPUT)
    METADATA.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"\n배포 산출물: {OUTPUT}")


if __name__ == "__main__":
    main()
