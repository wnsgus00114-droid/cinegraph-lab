.PHONY: data up down test k8s
data:
	bash scripts/download_data.sh
up: data
	docker compose up --build
down:
	docker compose down
test:
	PYTHONPATH=. python -m pytest -q
k8s: data
	docker build -f back/Dockerfile -t cinegraph-api:latest .
	docker build -f front/Dockerfile -t cinegraph-front:latest .
	kubectl apply -f k8s/namespace.yaml -f k8s/api.yaml -f k8s/frontend.yaml
