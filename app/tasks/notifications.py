"""Notification tasks. STUB."""
from app.tasks.celery_app import celery


@celery.task(bind=True, max_retries=3)
def send_welcome_email(self, student_id: str, course_id: str) -> None:
    """Send a 'welcome to the course' notification. TODO: integrate email provider."""
    raise NotImplementedError
