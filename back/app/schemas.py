from typing import Literal
from pydantic import BaseModel, Field

ModelName = Literal["lightgcn", "sasrec", "two_tower", "fusion"]


class RecommendRequest(BaseModel):
    liked_movie_ids: list[int] = Field(min_length=1, max_length=20)
    model: ModelName = "fusion"
    top_k: int = Field(default=10, ge=1, le=20)
    diversity: float = Field(default=0.35, ge=0, le=1)
    novelty: float = Field(default=0.25, ge=0, le=1)


class MovieResult(BaseModel):
    movie_id: int
    title: str
    genres: str
    score: float
    reason: str


class RecommendResponse(BaseModel):
    model: str
    engine_description: str
    recommendations: list[MovieResult]
    latency_ms: float
    api_trace_id: str

