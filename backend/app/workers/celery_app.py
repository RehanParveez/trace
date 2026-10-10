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
    "app.modules.drawings_boq.tasks",
    "app.modules.drawings_boq.calc_tasks",
    "app.modules.drawings_boq.recalculation.export_task",
  ],
)

celery_app.conf.update(
  task_default_queue = "default",
  task_routes={
    "app.modules.whatsapp.*": {"queue": "whatsapp_priority"},
    "app.workers.bim.*": {"queue": "bim_parsing"},
    "app.modules.subscriptions.*": {"queue": "billing"},
    "app.modules.drawings_boq.calc_tasks.calculate_run_task": {"queue": "calc_engine"},
    "app.modules.drawings_boq.calc_tasks.auto_run_task": {"queue": "default"},
    "app.modules.drawings_boq.calc_tasks.recover_*": {"queue": "default"},
    "app.modules.drawings_boq.calc_tasks.purge_*": {"queue": "default"},
    "app.modules.drawings_boq.calc_tasks.expire_*": {"queue": "default"},
    "app.modules.drawings_boq.tasks.parse_drawing_task": {"queue": "bim_parsing"},
    "app.modules.drawings_boq.recalculation.export_task.*": {"queue": "export"},
  },
  task_acks_late=True,
  worker_prefetch_multiplier=1,
  worker_max_memory_per_child=int(settings.calc_worker_max_memory_kb),
  task_track_started=True,
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
    "recover-stale-calculation-runs": {
      "task": "app.modules.drawings_boq.calc_tasks.recover_stale_runs_task",
      "schedule": 120.0,
    },
    "recover-lost-exports": {
      "task": "app.modules.drawings_boq.calc_tasks.recover_exports_task",
      "schedule": 300.0,
    },
    "reap-stuck-photo-messages": {
      "task": "app.modules.whatsapp.tasks.reap_stuck_photo_messages",
      "schedule": 300.0,
    },
    "purge-calculation-staging": {
      "task": "app.modules.drawings_boq.calc_tasks.purge_staging_task",
      "schedule": crontab(hour=2, minute=30),
    },
    "expire-export-files": {
      "task": "app.modules.drawings_boq.calc_tasks.expire_export_files_task",
      "schedule": crontab(hour=3, minute=15),
    },
  },
)