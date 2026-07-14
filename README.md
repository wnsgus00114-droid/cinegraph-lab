# CineGraph Lab — novelty-aware multi-model movie recommender

CineGraph Lab is an end-to-end MLOps recommendation application. A user selects movies in Streamlit; Streamlit sends JSON to FastAPI; FastAPI runs one of four research-inspired retrieval engines and a diversity/novelty re-ranker; the result returns to the UI. Recommendation logic is deliberately absent from the frontend.

## Novelty and differentiators

- **Four selectable engines:** LightGCN-inspired graph propagation, SASRec-inspired ordered preference encoding, collaborative/content Two-Tower retrieval, and gated Fusion.
- **Novelty-aware recommendation:** a controllable long-tail score reduces popularity bias.
- **Diversity-aware slate:** Maximal Marginal Relevance avoids ten nearly identical results.
- **Explainability:** each result states genre affinity or cross-genre discovery and long-tail status.
- **MLOps:** API health/readiness, Docker Compose, Kubernetes manifests, resource limits, GitHub Actions tests, request trace IDs, and reproducible public-data ingestion.
- **Pub/Sub notifications:** Streamlit email subscription and recommendation publishing through an AWS SNS Topic, with a credential-free demo mode.

> This is a compact educational implementation of the cited architectural ideas, optimized for CPU demo deployment. It does not claim to reproduce the papers' benchmark results or full training protocols.

## Architecture

```text
Browser :8501 → Streamlit ─POST /recommend→ FastAPI :8000 → 4 retrieval engines
                                             ↓
                                novelty + MMR re-ranking
                                             ↓ JSON + trace ID
```

## Data provenance

| Dataset | Provider | Contents | License / usage |
|---|---|---|---|
| MovieLens latest-small | GroupLens Research, University of Minnesota | about 100k ratings, 9k movies, 600 users; ratings + timestamps + genres | Research dataset; follow the README bundled by GroupLens |

The dataset is downloaded directly from `https://files.grouplens.org/datasets/movielens/ml-latest-small.zip` by `scripts/download_data.sh`. Raw data is intentionally not committed, keeping the repository small and provenance reproducible. See the [official dataset page](https://grouplens.org/datasets/movielens/latest/).

## Run locally with Docker

Prerequisites: Docker Engine/Desktop, Compose v2, `curl`, and `unzip`.

```bash
make data
docker compose up --build
```

Open Streamlit at <http://localhost:8501> and FastAPI Swagger at <http://localhost:8000/docs>. Stop with `docker compose down`.

Quick API proof:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/recommend -H 'Content-Type: application/json' \
  -d '{"liked_movie_ids":[1,260],"model":"fusion","top_k":5,"diversity":0.35,"novelty":0.25}'
```

## Kubernetes (local)

For Docker Desktop Kubernetes, enable Kubernetes, then:

```bash
make k8s
kubectl -n cinegraph get pods,svc
kubectl -n cinegraph port-forward service/frontend 8501:8501
```

With kind/minikube, load the two local images into the cluster before applying manifests. Production deployments should push images to ECR and replace the image names.

## EC2 deployment

Allow inbound TCP **8501** (UI), **8000** (Swagger/demo only), and **22** (SSH, restricted to your IP) in the EC2 security group. Never commit a PEM key.

```bash
EC2_HOST=YOUR_PUBLIC_IP EC2_USER=ec2-user EC2_KEY=./your-key.pem bash scripts/deploy_ec2.sh
ssh -i ./your-key.pem ec2-user@YOUR_PUBLIC_IP 'cd ~/cinegraph && sudo docker compose ps'
```

For a long-lived public service, put TLS-capable Nginx/ALB in front, close port 8000 publicly, use an Elastic IP/domain, and store images in ECR.

## AWS SNS email Pub/Sub

Create a **Standard** SNS Topic in `us-east-1`, then give the EC2 instance role these least-privilege actions on that Topic: `sns:Subscribe` and `sns:Publish`. Configure its ARN before deployment:

```bash
export AWS_REGION=us-east-1
export SNS_TOPIC_ARN=arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:cinegraph-recommendations
docker compose up -d --build
```

The Streamlit sidebar submits an email endpoint to FastAPI, which calls SNS `Subscribe`. AWS sends a confirmation email; delivery starts only after the recipient selects **Confirm subscription**. The recommendation publish button sends one message to the Topic and SNS fans it out to every confirmed subscriber. If `SNS_TOPIC_ARN` is absent, the application clearly reports `demo` mode and sends no email. Never place AWS access keys in this repository or Docker image.

## Model behavior

| Engine | Signal | Best use |
|---|---|---|
| LightGCN | normalized user-item graph and low-rank propagation embedding | collaborative similarity |
| SASRec | ordered selection weights plus item recency representation | sequence-sensitive exploration |
| Two-Tower | collaborative item space concatenated with genre content space | retrieval with content awareness |
| Fusion | weighted agreement of all three, then novelty + MMR | robust default |

Cold-start is handled through movie genre features, but users must choose at least one catalog item. The API validates inputs, caps result count, excludes already-liked items, and emits latency plus a trace ID.

## Tests and repository safety

```bash
make data
python -m venv .venv && source .venv/bin/activate
pip install -r back/requirements.txt httpx pytest
pytest -q
git check-ignore -v *.pem '과제안내.md' '유튜브대본.md'
```

Downloaded data, trained artifacts, PEM files, the private assignment sheet, and the private YouTube script are excluded by `.gitignore` and `.dockerignore`.

## References

1. He, X. et al. (2020). [LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation](https://doi.org/10.1145/3397271.3401063), SIGIR.
2. Kang, W-C. & McAuley, J. (2018). [Self-Attentive Sequential Recommendation](https://doi.org/10.1109/ICDM.2018.00035), ICDM.
3. Yi, X. et al. (2019). [Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations](https://research.google/pubs/sampling-bias-corrected-neural-modeling-for-large-corpus-item-recommendations/), RecSys (two-tower retrieval).
4. Carbonell, J. & Goldstein, J. (1998). [The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries](https://doi.org/10.1145/290941.291025), SIGIR.
5. Harper, F. M. & Konstan, J. A. (2015). [The MovieLens Datasets: History and Context](https://doi.org/10.1145/2827872), ACM TiiS.

## License and responsible use

Application source is provided for educational use. MovieLens remains governed by its own terms. Recommendations are experimental; popularity and historical interaction data can encode bias, so the novelty control is visible rather than hidden.
