"""Notification tasks — one email per task, fire-and-forget (see celery_app.py).

Tasks take plain-string payloads (email address, names, titles) resolved by the
caller at dispatch time, so the sync worker never needs async DB access. Copy
speaks from the product's side: plain verbs, says exactly what happened.
"""
from app.tasks.celery_app import celery
from app.tasks.emailer import send_email

RETRY_DELAY_S = 30


@celery.task(bind=True, max_retries=3)
def send_registration_welcome(self, email: str, full_name: str, role: str) -> None:
    """Welcome a newly registered user to the platform."""
    first = full_name.split(" ")[0]
    if role == "instructor":
        next_step = (
            "Create your first course from the My Courses page — draft it, "
            "then publish when it's ready."
        )
    else:
        next_step = (
            "Browse the catalog and enroll in your first course — progress is "
            "tracked to the certificate."
        )
    try:
        send_email(
            to=email,
            subject="Welcome to SmartCourse",
            body=(
                f"Hi {first},\n\n"
                f"Your SmartCourse {role} account is ready.\n\n"
                f"{next_step}\n\n"
                "— SmartCourse"
            ),
        )
    except Exception as exc:  # pragma: no cover — retry path needs a live broker
        raise self.retry(exc=exc, countdown=RETRY_DELAY_S) from exc


@celery.task(bind=True, max_retries=3)
def send_course_welcome(self, email: str, full_name: str, course_title: str) -> None:
    """Welcome a student to a course they just enrolled in."""
    first = full_name.split(" ")[0]
    try:
        send_email(
            to=email,
            subject=f"You're enrolled: {course_title}",
            body=(
                f"Hi {first},\n\n"
                f"You're enrolled in “{course_title}”.\n\n"
                "Work through the modules at your own pace — your progress is "
                "saved as you go, and finishing every lesson earns your "
                "certificate.\n\n"
                "— SmartCourse"
            ),
        )
    except Exception as exc:  # pragma: no cover — retry path needs a live broker
        raise self.retry(exc=exc, countdown=RETRY_DELAY_S) from exc


@celery.task(bind=True, max_retries=3)
def send_completion_congrats(
    self, email: str, full_name: str, course_title: str, certificate_serial: str
) -> None:
    """Congratulate a student on completing a course; include the certificate serial."""
    first = full_name.split(" ")[0]
    try:
        send_email(
            to=email,
            subject=f"Course complete: {course_title}",
            body=(
                f"Hi {first},\n\n"
                f"You completed “{course_title}” — congratulations.\n\n"
                f"Your certificate is issued: {certificate_serial}\n"
                "View it any time from My Learning.\n\n"
                "— SmartCourse"
            ),
        )
    except Exception as exc:  # pragma: no cover — retry path needs a live broker
        raise self.retry(exc=exc, countdown=RETRY_DELAY_S) from exc
