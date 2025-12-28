"""
Celery application for MadanSara async task processing
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    'madansara',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,
    beat_schedule={
        'segment-audiences-daily': {
            'task': 'app.tasks.segmentation.segment_all_audiences',
            'schedule': crontab(hour=8, minute=0),
        },
    },
)

celery_app.autodiscover_tasks(['app.services', 'app.tasks'])

@celery_app.task(name='app.celery_app.health_check')
def health_check():
    return {'status': 'healthy', 'service': 'madansara-celery'}
