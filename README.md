# 씨네그래프 랩(CineGraph Lab)

> 최신 추천 연구 아이디어와 MLOps를 결합한 새로움·다양성 기반 영화 추천 서비스

- **배포 웹사이트:** <http://18.205.104.199:8501>
- **FastAPI 문서:** <http://18.205.104.199:8000/docs>

씨네그래프 랩은 Streamlit, FastAPI, Docker, Kubernetes, AWS EC2, AWS SNS를 하나의 흐름으로 연결한 영화 추천 MLOps 프로젝트입니다. 사용자가 재미있게 본 영화를 선택하면 Streamlit이 FastAPI에 HTTP 요청을 보내고, FastAPI가 추천 엔진을 실행해 JSON 결과를 반환합니다.

프론트엔드에서 추천을 직접 계산하지 않으며, 모든 추천 결과는 별도 FastAPI 컨테이너에서 생성됩니다.

## 핵심 기능

- 영화 검색 및 다중 선택을 통한 개인 선호 입력
- Streamlit과 FastAPI 사이의 실제 HTTP/JSON 통신
- LightGCN, SASRec, Two-Tower, Fusion, 실제 학습한 MLP 총 5개 추천 엔진 비교
- 인기작 위주 편향을 줄이는 새로움(novelty) 조절
- 비슷한 장르의 반복을 줄이는 MMR 다양성 재정렬
- 장르 일치, 새로운 장르 발견, 숨은 작품 여부를 표시하는 추천 이유
- AWS SNS Pub/Sub 기반 이메일 구독 및 추천 알림 발행
- Docker Compose 기반 프론트엔드·백엔드 분리 배포
- Kubernetes Deployment, Service, 준비 상태 검사, 자원 제한
- GitHub Actions 기반 데이터 준비, API 통합 테스트, Compose 구성 검증
- API 응답 시간과 요청 추적 ID를 이용한 관찰 가능성

## 차별성과 새로운 점

일반적인 인기순 또는 단순 장르 필터 방식을 넘어, 서로 다른 추천 신호를 하나의 서비스에서 비교할 수 있게 구성했습니다. 사용자는 다양성과 새로움을 직접 조절할 수 있으며, 이를 통해 가장 인기 있는 영화만 반복 노출되는 편향을 완화합니다.

추천 결과는 AWS SNS Topic에 메시지로 발행되며, SNS가 확인된 이메일 구독자 전체에게 알림을 팬아웃합니다. 추천 기능을 단순 웹 페이지에 머물게 하지 않고 이벤트 기반 메시징으로 확장했습니다.



## 전체 구조

```text
사용자 브라우저 :8501
          │
          ▼
     Streamlit UI
          │  POST /recommend (JSON)
          ▼
      FastAPI :8000
          │
          ├─ LightGCN 기반 그래프 탐색
          ├─ SASRec 기반 시퀀스 표현
          ├─ Two-Tower 협업·장르 탐색
          ├─ Fusion 앙상블
          └─ MLP(64→32) 학습 모델
                    │
                    ▼
          새로움 점수 + MMR 다양성 재정렬
                    │
                    ├─ JSON 응답 → Streamlit 결과 표시
                    └─ AWS SNS Topic → 이메일 구독자
```

## 폴더 구조

```text
.
├─ front/                  # Streamlit 프론트엔드와 Dockerfile
├─ back/app/               # FastAPI, 추천 엔진, SNS 알림
├─ k8s/                   # Kubernetes 매니페스트
├─ scripts/               # 데이터, MLP 학습, EC2 배포
├─ tests/                 # API 통합 테스트
├─ .github/workflows/     # GitHub Actions CI
├─ docker-compose.yml
└─ Makefile
```

## 데이터 출처

| 항목 | 내용 |
|---|---|
| 데이터셋 | MovieLens latest-small |
| 제공 기관 | 미네소타 대학 GroupLens Research |
| 주요 내용 | 약 10만 개 평점, 9천 개 영화, 600명 사용자, 타임스탬프, 장르 |
| 공식 페이지 | [GroupLens MovieLens](https://grouplens.org/datasets/movielens/latest/) |
| 다운로드 주소 | `https://files.grouplens.org/datasets/movielens/ml-latest-small.zip` |

`scripts/download_data.sh`가 GroupLens 공식 주소에서 `movies.csv`와 `ratings.csv`를 재현 가능하게 다운로드합니다. 저장소 크기와 저작권·데이터 출처 관리를 위해 원본 CSV는 GitHub에 커밋하지 않습니다.

## 추천 엔진 5종

| 엔진 | 활용 신호 | 특징 |
|---|---|---|
| LightGCN | 정규화한 사용자–영화 상호작용 그래프 | 협업적 유사성 탐색 |
| SASRec | 선택 순서와 영화의 최근성 | 시퀀스에 민감한 탐색 |
| Two-Tower | 협업 영화 표현과 장르 콘텐츠 표현 | 상호작용과 콘텐츠 정보 결합 |
| Fusion | 위 세 신호의 가중 앙상블 | 새로움·MMR까지 결합한 기본 추천 엔진 |
| MLP | 사용자 선호, 영화 장르, 선호×장르 교차 특징, 인기도 | 64→32 은닉층이 비선형 평점 관계를 학습 |

사용자가 선택한 영화는 결과에서 제외됩니다. API는 입력 범위와 결과 개수를 검증하고, 응답 시간과 요청별 UUID를 함께 반환합니다. 사용자 이력이 없는 콜드 스타트 상황에서는 선택한 영화의 장르 표현을 활용합니다.

## MLP 학습·배포 MLOps 흐름

MLP는 실행 시 임의로 생성되는 모델이 아니라 MovieLens 평점을 학습한 배포 산출물입니다. 학습 컨테이너와 서빙 컨테이너를 분리했습니다.

```text
MovieLens 다운로드
  → 학습 특징 생성
  → Docker trainer에서 MLPRegressor(64, 32) 학습
  → RMSE·MAE 평가
  → artifacts/mlp_recommender.joblib 생성
  → Docker API 이미지에 모델 포함
  → FastAPI 시작 시 모델 로드
  → Streamlit에서 MLP 엔진 선택
```

학습 재현:

```bash
make train-mlp
cat artifacts/mlp_metrics.json
```

로컬 배포:

```bash
make deploy-mlp
curl http://localhost:8000/health
```

`mlp_model_loaded` 값이 `true`면 학습한 모델이 정상 로드된 상태입니다. 모델 파일과 평가 JSON은 재생성 가능한 산출물이므로 Git에 추적하지 않습니다.

영상에서 EC2로 배포할 때:

```bash
make train-mlp
cat artifacts/mlp_metrics.json
EC2_USER=ec2-user bash scripts/deploy_ec2.sh

curl http://18.205.104.199:8000/health
```

마지막으로 Streamlit의 `MLP 학습 모델`을 선택해 추천 결과를 보여주면 학습–평가–패키징–배포–서빙의 전체 MLOps 흐름을 증명할 수 있습니다.

## 로컬 Docker 실행

### 필요 환경

- Docker Engine 또는 Docker Desktop
- Docker Compose v2
- `curl`, `unzip`

### 실행

```bash
make data
docker compose up --build
```

실행 후 접속 주소:

- Streamlit: <http://localhost:8501>
- FastAPI Swagger: <http://localhost:8000/docs>

종료:

```bash
docker compose down
```

### API 통신 확인

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{"liked_movie_ids":[1,260],"model":"fusion","top_k":5,"diversity":0.35,"novelty":0.25}'
```

## Kubernetes 로컬 배포

Docker Desktop에서 Kubernetes를 활성화한 후 실행합니다.

```bash
make k8s
kubectl -n cinegraph get pods,svc
kubectl -n cinegraph port-forward service/frontend 8501:8501
```

kind 또는 minikube를 사용할 경우 매니페스트를 적용하기 전에 `cinegraph-api`, `cinegraph-front` 이미지를 클러스터에 로드해야 합니다. 운영 환경에서는 ECR에 이미지를 푸시한 후 매니페스트의 이미지 주소를 교체하는 방식이 적합합니다.

## AWS EC2 배포

보안 그룹 인바운드 규칙:

| 포트 | 용도 | 권장 설정 |
|---:|---|---|
| 22 | SSH | 관리자 공인 IP로 제한 |
| 8501 | Streamlit UI | 데모 시 `0.0.0.0/0` |
| 8000 | FastAPI Swagger | 데모 시만 공개 |

```bash
EC2_HOST=YOUR_PUBLIC_IP \
EC2_USER=ec2-user \
EC2_KEY=./your-key.pem \
bash scripts/deploy_ec2.sh

ssh -i ./your-key.pem ec2-user@YOUR_PUBLIC_IP \
  'cd ~/cinegraph && sudo docker compose ps'
```

PEM 키는 절대 GitHub에 커밋하지 않습니다. 장기 운영 시에는 Nginx 또는 ALB에서 TLS를 종료하고, 8000번 포트의 외부 공개를 차단하며, Elastic IP·도메인·ECR을 사용하는 구성이 적합합니다.

## AWS SNS Pub/Sub 이메일 알림

### 동작 흐름

1. 사용자가 Streamlit 사이드바에 이메일을 입력합니다.
2. Streamlit이 FastAPI의 `/notifications/subscribe`를 호출합니다.
3. FastAPI가 SNS Topic에 이메일 엔드포인트 구독을 요청합니다.
4. AWS가 확인 메일을 발송합니다.
5. 사용자가 **Confirm subscription**을 누른 후부터 알림이 전달됩니다.
6. 추천 알림이 SNS Topic에 발행되면 SNS가 모든 확인된 구독자에게 이메일을 전송합니다.

### 설정

`us-east-1`에 Standard SNS Topic을 생성하고 EC2 IAM 역할에 해당 Topic에 대한 `sns:Subscribe`, `sns:Publish` 최소 권한을 부여합니다.

```bash
export AWS_REGION=us-east-1
export SNS_TOPIC_ARN=arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:cinegraph-recommendations
docker compose up -d --build
```

`SNS_TOPIC_ARN`이 없으면 앱은 메일을 발송하지 않는 `demo` 모드로 동작합니다. AWS 액세스 키를 소스 코드, Docker 이미지, GitHub에 저장해서는 안 됩니다.

## 테스트

```bash
make data
python -m venv .venv
source .venv/bin/activate
pip install -r back/requirements.txt httpx pytest
make test
```

통합 테스트는 다음을 확인합니다.

- FastAPI 헬스체크
- 추천 요청과 결과 개수
- SNS 구독 API
- SNS 메시지 발행 API
- Docker Compose 구성 유효성
## 한계와 개선 방향

- MovieLens 영화 제목과 장르는 원본 데이터에 따라 영문으로 표시됩니다.
- 실시간 사용자 이력을 영구 저장하지 않으며, 현재 세션의 선택 정보를 기반으로 추천합니다.
- 실제 대규모 운영 시에는 사전 학습한 임베딩 산출물, 버전 관리, A/B 테스트, 피드백 루프가 필요합니다.
- 과거 상호작용 데이터에 편향이 포함될 수 있으므로 새로움 조절 기능을 숨기지 않고 사용자에게 공개했습니다.

## 참고 문헌

1. He, X. et al. (2020). [LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation](https://doi.org/10.1145/3397271.3401063), SIGIR.
2. Kang, W-C. & McAuley, J. (2018). [Self-Attentive Sequential Recommendation](https://doi.org/10.1109/ICDM.2018.00035), ICDM.
3. Yi, X. et al. (2019). [Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations](https://research.google/pubs/sampling-bias-corrected-neural-modeling-for-large-corpus-item-recommendations/), RecSys.
4. Carbonell, J. & Goldstein, J. (1998). [The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries](https://doi.org/10.1145/290941.291025), SIGIR.
5. Harper, F. M. & Konstan, J. A. (2015). [The MovieLens Datasets: History and Context](https://doi.org/10.1145/2827872), ACM Transactions on Interactive Intelligent Systems.

