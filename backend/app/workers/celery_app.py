from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
  "trace",
  broker=settings.celery_broker_url,
  backend=settings.celery_result_backend,
  include=[
    "app.modules.whatsapp.tasks",
    "app.modules.subscriptions.tasks",
  ],
)

celery_app.conf.update(
  task_default_queue = "default",
  task_routes={
    "app.modules.whatsapp.*": {"queue": "whatsapp_priority"},
    "app.workers.bim.*": {"queue": "bim_parsing"},
    "app.modules.subscriptions.*": {"queue": "billing"},
  },
  task_serializer = "json",
  result_serializer = "json",
  accept_content=["json"],
  timezone=settings.default_timezone,
  enable_utc=True,
  beat_schedule={
    "roll-expired-subscriptions": {
      "task": "app.modules.subscriptions.tasks.roll_expired_subscriptions_task",
      "schedule": crontab(minute=0),
    },
  },
)