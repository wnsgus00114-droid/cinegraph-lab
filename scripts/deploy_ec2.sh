#!/usr/bin/env bash
set -euo pipefail
HOST="${EC2_HOST:-18.205.104.199}"
USER="${EC2_USER:-ec2-user}"
KEY="${EC2_KEY:-labsuser.pem}"
chmod 600 "$KEY"
tar --exclude='.git' --exclude='*.pem' --exclude='과제안내.md' --exclude='유튜브대본.md' \
  --exclude='.venv' -czf /tmp/cinegraph.tar.gz .
ssh -o StrictHostKeyChecking=accept-new -i "$KEY" "$USER@$HOST" 'mkdir -p ~/cinegraph'
scp -i "$KEY" /tmp/cinegraph.tar.gz "$USER@$HOST:~/cinegraph/"
ssh -i "$KEY" "$USER@$HOST" 'cd ~/cinegraph && tar xzf cinegraph.tar.gz && \
  (command -v docker >/dev/null || \
    if command -v dnf >/dev/null; then sudo dnf install -y docker && sudo systemctl enable --now docker; \
    else sudo apt-get update && sudo apt-get install -y docker.io; fi) && \
  (sudo docker compose version >/dev/null 2>&1 || \
    (sudo mkdir -p /usr/local/lib/docker/cli-plugins && \
     sudo curl -fsSL https://github.com/docker/compose/releases/download/v2.39.1/docker-compose-linux-x86_64 \
       -o /usr/local/lib/docker/cli-plugins/docker-compose && \
     sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose)) && \
  sudo docker compose up -d --build'
printf 'Deployed: http://%s:8501 (API docs: http://%s:8000/docs)\n' "$HOST" "$HOST"
