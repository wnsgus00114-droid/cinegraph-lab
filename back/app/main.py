import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .recommender import MODEL_DESCRIPTIONS, Recommender
from .notifications import NotificationService
from .schemas import (PublishRequest, PublishResponse, RecommendRequest, RecommendResponse,
                      SubscribeRequest, SubscribeResponse)

app = FastAPI(title="씨네그래프 랩 추천 API", description="MovieLens 기반 다중 모델 영화 추천 서비스", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
engine: Recommender | None = None
notifications = NotificationService()


@app.on_event("startup")
def load_engine():
    global engine
    engine = Recommender()


@app.get("/health")
def health():
    return {"status": "healthy", "models": list(MODEL_DESCRIPTIONS),
            "mlp_model_loaded": bool(engine and engine.mlp_loaded),
            "notification_mode": notifications.mode}


@app.get("/movies")
def movies(query: str = "", limit: int = 100):
    assert engine is not None
    frame = engine.state.movies
    if query:
        frame = frame[frame.title.str.contains(query, case=False, regex=False)]
    return frame[["movieId", "title", "genres"]].head(min(limit, 500)).to_dict("records")


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    started = time.perf_counter()
    try:
        assert engine is not None
        results = engine.recommend(req.liked_movie_ids, req.model, req.top_k, req.diversity, req.novelty)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RecommendResponse(model=req.model, engine_description=MODEL_DESCRIPTIONS[req.model],
        recommendations=results, latency_ms=round((time.perf_counter()-started)*1000, 2),
        api_trace_id=str(uuid.uuid4()))


@app.post("/notifications/subscribe", response_model=SubscribeResponse, tags=["알림 Pub/Sub"])
def subscribe(req: SubscribeRequest):
    """SNS 이메일 구독을 요청합니다."""
    try:
        return notifications.subscribe(req.email)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/notifications/publish", response_model=PublishResponse, tags=["알림 Pub/Sub"])
def publish(req: PublishRequest):
    """SNS Topic에 알림을 발행해 확인된 모든 구독자에게 전달합니다."""
    try:
        return notifications.publish(req.subject, req.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
