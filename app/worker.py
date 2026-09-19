import logging

from celery import Celery

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AMLAlertWorker")

celery_app = Celery("aml_tasks", broker=settings.REDIS_URL, backend=None)
celery_app.conf.update(
    task_ignore_result=True,
    broker_connection_retry_on_startup=False,
    broker_connection_max_retries=1,
    broker_connection_timeout=0.2,
    task_publish_retry=False,
)


def log_investigator_alert(alert_payload: dict) -> dict:
    logger.warning(
        f"[HIGH RISK TRIAGE] Entity: {alert_payload.get('entity_id')} | "
        f"Dataset: {alert_payload.get('dataset')} | "
        f"Tier: {alert_payload.get('risk_tier')} | "
        f"Score: {alert_payload.get('risk_score')}"
    )
    return {"status": "QUEUED", "entity_id": alert_payload.get("entity_id")}


@celery_app.task(name="tasks.dispatch_investigator_alert")
def dispatch_investigator_alert(alert_payload: dict):
    return log_investigator_alert(alert_payload)

