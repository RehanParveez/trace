from app.workers.celery_app import celery_app

@celery_app.task(name="app.workers.whatsapp.health_task")
def health_task() -> str:
  return "whatsapp-worker-ready"