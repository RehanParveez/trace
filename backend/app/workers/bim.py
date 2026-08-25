from app.workers.celery_app import celery_app

@celery_app.task(name = "app.workers.bim.health_task")
def health_task() -> str:
  return "bim-worker-ready"