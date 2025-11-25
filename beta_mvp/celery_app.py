import os

from celery import Celery


BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
BACKEND_URL = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "agentic_multilingual_news_verification",
    broker=BROKER_URL,
    backend=BACKEND_URL,
)

celery_app.conf.task_queues = []  # use default queue; process_post will be routed by name
