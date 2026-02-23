# HR workflow nodes: upload, CV, job skills, evaluation, notifications

from backend.services.hr.graph.nodes.upload import upload_cv_node
from backend.services.hr.graph.nodes.cv import (
    extract_cv_data_node,
    generate_summary_node,
)
from backend.services.hr.graph.nodes.job_skills import extract_job_skills_node
from backend.services.hr.graph.nodes.evaluation import (
    evaluate_candidate_node,
    skills_match_node,
    score_decision_node,
    route_on_score,
)
from backend.services.hr.graph.nodes.notifications import (
    fan_out_notifications,
    send_hr_email_node,
    send_slack_notification_node,
    send_whatsapp_node,
)
from backend.services.hr.graph.nodes.persistence import save_candidate_to_mongodb

__all__ = [
    "upload_cv_node",
    "extract_cv_data_node",
    "generate_summary_node",
    "extract_job_skills_node",
    "evaluate_candidate_node",
    "skills_match_node",
    "score_decision_node",
    "route_on_score",
    "fan_out_notifications",
    "send_hr_email_node",
    "send_slack_notification_node",
    "send_whatsapp_node",
    "save_candidate_to_mongodb",
]
