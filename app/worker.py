import logging
from celery import Celery
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AMLAlertWorker")

celery_app = Celery("aml_tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)


@celery_app.task(name="tasks.dispatch_investigator_alert")
def dispatch_investigator_alert(alert_payload: dict):
    logger.warning(
        f"[HIGH RISK TRIAGE] Entity: {alert_payload.get('entity_id')} | "
        f"Dataset: {alert_payload.get('dataset')} | "
        f"Tier: {alert_payload.get('risk_tier')} | "
        f"Score: {alert_payload.get('risk_score')}"
    )
    return {"status": "QUEUED", "entity_id": alert_payload.get("entity_id")}
