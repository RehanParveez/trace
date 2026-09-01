from celery import Celery
from app.core.config import settings

celery_app = Celery(
  "trace",
  broker=settings.celery_broker_url,
  backend=settings.celery_result_backend,
  include=[
    "app.modules.whatsapp.tasks",
  ],
)

celery_app.conf.update(
  task_default_queue = "default",
  task_routes={
    "app.modules.whatsapp.*": {"queue": "whatsapp_priority"},
    "app.workers.bim.*": {"queue": "bim_parsing"},
  },
  task_serializer = "json",
  result_serializer = "json",
  accept_content=["json"],
  timezone=settings.default_timezone,
  enable_utc=True,
)