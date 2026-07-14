"""AWS SNS pub/sub adapter with a safe credential-free demonstration mode."""
from __future__ import annotations

import hashlib
import os
import uuid

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


class NotificationService:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.topic_arn = os.getenv("SNS_TOPIC_ARN", "").strip()
        self.demo_subscribers: set[str] = set()
        self._client = boto3.client("sns", region_name=self.region) if self.topic_arn else None

    @property
    def mode(self) -> str:
        return "aws_sns" if self.topic_arn else "demo"

    def subscribe(self, email: str) -> dict[str, str]:
        normalized = email.strip().lower()
        if not self.topic_arn:
            self.demo_subscribers.add(hashlib.sha256(normalized.encode()).hexdigest())
            return {"status": "demo", "mode": "demo",
                    "message": "데모 구독이 등록되었습니다. SNS_TOPIC_ARN을 설정하면 실제 확인 메일이 발송됩니다."}
        try:
            self._client.subscribe(TopicArn=self.topic_arn, Protocol="email", Endpoint=normalized,
                                   ReturnSubscriptionArn=True)
        except (BotoCoreError, ClientError, NoCredentialsError) as exc:
            raise RuntimeError(f"AWS SNS 구독 요청 실패: {exc}") from exc
        return {"status": "pending_confirmation", "mode": "aws_sns",
                "message": "AWS SNS 확인 메일을 보냈습니다. 메일의 Confirm subscription을 누르면 구독이 완료됩니다."}

    def publish(self, subject: str, message: str) -> dict[str, str]:
        if not self.topic_arn:
            return {"status": "demo", "mode": "demo", "message_id": f"demo-{uuid.uuid4()}"}
        try:
            response = self._client.publish(TopicArn=self.topic_arn, Subject=subject, Message=message)
        except (BotoCoreError, ClientError, NoCredentialsError) as exc:
            raise RuntimeError(f"AWS SNS 메시지 발행 실패: {exc}") from exc
        return {"status": "published", "mode": "aws_sns", "message_id": response["MessageId"]}
