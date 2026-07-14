import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .recommender import MODEL_DESCRIPTIONS, Recommender
from .schemas import RecommendRequest, RecommendResponse

app = FastAPI(title="CineGraph Lab API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
engine: Recommender | None = None


@app.on_event("startup")
def load_engine():
    global engine
    engine = Recommender()


@app.get("/health")
def health():
    return {"status": "healthy", "models": list(MODEL_DESCRIPTIONS)}


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

