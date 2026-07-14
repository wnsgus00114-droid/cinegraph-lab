.PHONY: data train-mlp up down test k8s deploy-mlp
data:
	bash scripts/download_data.sh
train-mlp: data
	docker compose --profile training run --rm trainer
up: data train-mlp
	docker compose up --build
down:
	docker compose down
test:
	PYTHONPATH=. python -m pytest -q
k8s: data
	docker build -f back/Dockerfile -t cinegraph-api:latest .
	docker build -f front/Dockerfile -t cinegraph-front:latest .
	kubectl apply -f k8s/namespace.yaml -f k8s/api.yaml -f k8s/frontend.yaml
deploy-mlp: train-mlp
	docker compose up -d --build --force-recreate
	curl -fsS http://localhost:8000/health
