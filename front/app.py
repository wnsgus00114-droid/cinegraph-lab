import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="씨네그래프 랩", page_icon="🎬", layout="wide")
st.title("🎬 씨네그래프 랩")
st.caption("그래프 × 시퀀스 × 의미 기반 탐색으로 만나는 나만의 영화 추천")

@st.cache_data(ttl=300)
def get_movies(query=""):
    r = requests.get(f"{API_URL}/movies", params={"query": query, "limit": 300}, timeout=10)
    r.raise_for_status()
    return r.json()

with st.sidebar:
    st.header("추천 실험실")
    model = st.selectbox("추천 엔진", ["fusion", "lightgcn", "sasrec", "two_tower"],
        format_func=lambda x: {"fusion":"퓨전 (추천)", "lightgcn":"LightGCN 그래프", "sasrec":"SASRec 시퀀스", "two_tower":"Two-Tower 탐색"}[x])
    top_k = st.slider("추천 결과 개수", 3, 15, 8)
    diversity = st.slider("다양성", 0.0, 1.0, 0.35, 0.05,
                          help="높일수록 서로 다른 장르의 영화를 보여줍니다.")
    novelty = st.slider("새로움 · 숨은 작품 발견", 0.0, 1.0, 0.25, 0.05,
                        help="높일수록 인기작 외의 숨은 영화를 더 적극적으로 찾습니다.")
    st.info("화면에서 직접 계산하지 않고, 모든 추천을 FastAPI 백엔드가 처리합니다.")
    with st.expander("🔔 새 추천 알림 구독", expanded=False):
        st.write("AWS SNS Pub/Sub으로 새 영화 추천 소식을 이메일로 받아보세요.")
        email = st.text_input("알림을 받을 이메일", placeholder="name@example.com")
        if st.button("이메일 알림 구독", use_container_width=True):
            if not email:
                st.warning("이메일을 입력해 주세요.")
            else:
                try:
                    response = requests.post(f"{API_URL}/notifications/subscribe",
                                             json={"email": email}, timeout=15)
                    response.raise_for_status()
                    subscription = response.json()
                    if subscription["mode"] == "aws_sns":
                        st.success(subscription["message"])
                    else:
                        st.info(subscription["message"])
                except requests.RequestException as exc:
                    st.error(f"구독 요청에 실패했습니다: {exc}")

query = st.text_input("영화 검색", placeholder="영문 제목으로 검색해 보세요: Toy Story, Matrix, Star Wars")
try:
    movies = get_movies(query)
except Exception as exc:
    st.error(f"FastAPI 서버({API_URL})에 연결할 수 없습니다: {exc}")
    st.stop()
labels = {f"{m['title']}  —  {m['genres']}": m["movieId"] for m in movies}
selected = st.multiselect("재미있게 본 영화를 1–20개 선택하세요. 선택 순서도 선호 신호로 활용합니다.", labels)

if st.button("🧠 맞춤 영화 추천받기", type="primary", use_container_width=True):
    if not selected:
        st.warning("좋아하는 영화를 하나 이상 선택해 주세요.")
    else:
        payload = {"liked_movie_ids": [labels[x] for x in selected], "model": model,
                   "top_k": top_k, "diversity": diversity, "novelty": novelty}
        with st.spinner("FastAPI가 그래프를 탐색하고 새로움과 다양성을 반영하는 중입니다…"):
            try:
                response = requests.post(f"{API_URL}/recommend", json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc:
                st.error(f"추천 API 요청에 실패했습니다: {exc}")
                st.stop()
        st.success(f"FastAPI가 {data['latency_ms']}ms 만에 {len(data['recommendations'])}개의 영화를 추천했습니다.")
        st.caption(f"사용 엔진: {data['engine_description']} · 요청 추적 ID: {data['api_trace_id']}")
        for rank, movie in enumerate(data["recommendations"], 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 8])
                col1.metric("순위", f"#{rank}")
                col2.subheader(movie["title"])
                col2.write(movie["genres"])
                col2.caption(f"{movie['reason']} · 관련도 {movie['score']:.3f}")
        message_lines = ["씨네그래프 랩이 추천한 영화입니다.", ""]
        message_lines += [f"{i}. {m['title']} - {m['reason']}" for i, m in enumerate(data["recommendations"][:5], 1)]
        if st.button("📣 이 추천 목록을 구독자에게 알림으로 발행", use_container_width=True):
            try:
                response = requests.post(f"{API_URL}/notifications/publish",
                    json={"subject": "씨네그래프 랩 새 영화 추천", "message": "\n".join(message_lines)}, timeout=15)
                response.raise_for_status()
                published = response.json()
                if published["mode"] == "aws_sns":
                    st.success(f"구독자에게 알림을 발행했습니다. 메시지 ID: {published['message_id']}")
                else:
                    st.info("데모 발행이 완료됐습니다. AWS SNS 설정 후 실제 이메일이 발송됩니다.")
            except requests.RequestException as exc:
                st.error(f"알림 발행에 실패했습니다: {exc}")
