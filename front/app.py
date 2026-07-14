import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="CineGraph Lab", page_icon="🎬", layout="wide")
st.title("🎬 CineGraph Lab")
st.caption("Graph × Sequence × Semantic retrieval, with diversity and novelty you control")

@st.cache_data(ttl=300)
def get_movies(query=""):
    r = requests.get(f"{API_URL}/movies", params={"query": query, "limit": 300}, timeout=10)
    r.raise_for_status()
    return r.json()

with st.sidebar:
    st.header("Recommendation laboratory")
    model = st.selectbox("Engine", ["fusion", "lightgcn", "sasrec", "two_tower"],
        format_func=lambda x: {"fusion":"Fusion (recommended)", "lightgcn":"LightGCN", "sasrec":"SASRec", "two_tower":"Two-Tower"}[x])
    top_k = st.slider("Number of results", 3, 15, 8)
    diversity = st.slider("Diversity", 0.0, 1.0, 0.35, 0.05)
    novelty = st.slider("Novelty / long-tail discovery", 0.0, 1.0, 0.25, 0.05)
    st.info("The UI never computes recommendations. Every result comes from FastAPI.")

query = st.text_input("Search the MovieLens catalog", placeholder="Try: Toy Story, Matrix, Star Wars")
try:
    movies = get_movies(query)
except Exception as exc:
    st.error(f"FastAPI is not reachable at {API_URL}: {exc}")
    st.stop()
labels = {f"{m['title']}  —  {m['genres']}": m["movieId"] for m in movies}
selected = st.multiselect("Choose 1–20 movies you enjoyed (selection order is treated as preference sequence)", labels)

if st.button("🧠 Generate intelligent recommendations", type="primary", use_container_width=True):
    if not selected:
        st.warning("Please select at least one movie.")
    else:
        payload = {"liked_movie_ids": [labels[x] for x in selected], "model": model,
                   "top_k": top_k, "diversity": diversity, "novelty": novelty}
        with st.spinner("FastAPI is running graph retrieval and novelty-aware re-ranking…"):
            try:
                response = requests.post(f"{API_URL}/recommend", json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as exc:
                st.error(f"Recommendation API failed: {exc}")
                st.stop()
        st.success(f"FastAPI returned {len(data['recommendations'])} results in {data['latency_ms']} ms")
        st.caption(f"Engine: {data['engine_description']} · trace: {data['api_trace_id']}")
        for rank, movie in enumerate(data["recommendations"], 1):
            with st.container(border=True):
                col1, col2 = st.columns([1, 8])
                col1.metric("Rank", f"#{rank}")
                col2.subheader(movie["title"])
                col2.write(movie["genres"])
                col2.caption(f"{movie['reason']} · relevance {movie['score']:.3f}")

