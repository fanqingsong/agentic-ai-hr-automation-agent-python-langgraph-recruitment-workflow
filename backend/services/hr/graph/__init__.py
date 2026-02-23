# HR workflow graph (CV extraction + job evaluation)

from backend.services.hr.graph.cv_extraction_workflow import create_cv_extraction_workflow
from backend.services.hr.graph.job_evaluation_workflow import create_job_evaluation_workflow

__all__ = [
    "create_cv_extraction_workflow",
    "create_job_evaluation_workflow",
]
