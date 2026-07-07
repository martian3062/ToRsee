from config.celery import app

from .services import IngestionRunner


@app.task(name="jobs.run_ingestion_job")
def run_ingestion_job(job_id: str) -> str:
    job = IngestionRunner().run(job_id)
    return str(job.id)
