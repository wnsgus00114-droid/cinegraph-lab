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


class SubscribeRequest(BaseModel):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=254)


class SubscribeResponse(BaseModel):
    status: Literal["pending_confirmation", "demo"]
    message: str
    mode: Literal["aws_sns", "demo"]


class PublishRequest(BaseModel):
    subject: str = Field(default="씨네그래프 랩 새 영화 추천", min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=5000)


class PublishResponse(BaseModel):
    status: Literal["published", "demo"]
    message_id: str
    mode: Literal["aws_sns", "demo"]
