# ============================================================================
# HR / AGENT SCHEMAS (LangGraph state, evaluation, CV extraction)
# ============================================================================

from typing import TypedDict, Annotated, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class PersonalData(BaseModel):
    """Personal information extracted from CV"""
    fullName: str = Field(description="Candidate's full name")
    phoneNumber: str = Field(default="Not provided", description="Phone number")
    birthdate: str = Field(default="Not provided", description="Birthdate in YYYY-MM-DD format")
    githubUrl: str = Field(default="Not provided", description="Github profile url")
    linkedinUrl: str = Field(default="Not provided", description="Linkedin profile url")
    city: str = Field(default="Not provided", description="City of residence")


class Education(BaseModel):
    """Educational background"""
    degree: str = Field(description="Degree name")
    institution: str = Field(description="Institution name")
    year: str = Field(description="Graduation year or period")


class JobHistory(BaseModel):
    """Job history entry"""
    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    duration: str = Field(description="Employment duration")


class Qualifications(BaseModel):
    """Professional qualifications"""
    education: list[Education] = Field(description="Educational background")
    jobHistory: list[JobHistory] = Field(description="Work experience")
    technicalSkills: list[str] = Field(description="Technical skills")


class SkillsMatch(BaseModel):
    """Skills match result"""
    strong: list[str] = Field(description="Strong matched skills with job description")
    partial: list[str] = Field(description="Partial matched skills with job description")
    missing: list[str] = Field(description="Missing skills with job description")


class CandidateEvaluation(BaseModel):
    """Final candidate evaluation"""
    score: int = Field(description="Score from 1-100", ge=1, le=100)
    reasoning: str = Field(description="Detailed reasoning for the score")
    strengths: List[str] = Field(description="Strengths of the candidate")
    decision: str = Field(description="Decision of the candidate")
    gaps: list[str] = Field(description="Gaps of the candidate")


class JobSkills(BaseModel):
    """Extract skills from job description"""
    tech_skills: List[str] = Field(
        description=(
            "Technical skills required for the role. "
            "Include programming languages, frameworks, tools, platforms, databases, "
            "cloud services, automation tools, APIs, etc. "
            "Normalize into short canonical names (e.g., 'Python', 'SQL', 'Docker')."
        )
    )
    soft_skills: List[str] = Field(
        description=(
            "Soft skills and non-technical competencies. "
            "Include communication, collaboration, leadership, problem solving, "
            "time management, adaptability, etc. "
            "Normalize into short canonical phrases (e.g., 'Project Management', 'Team Collaboration')."
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


def reduce_latest(current, new):
    return new


class CVExtractionState(TypedDict, total=False):
    """State for Graph1: CV upload -> extract -> summary -> save. No job/evaluation fields."""
    candidate_name: Annotated[str, reduce_latest]
    candidate_email: Annotated[str, reduce_latest]
    cv_file_path: Annotated[str, reduce_latest]
    cv_file_url: Annotated[str, reduce_latest]
    cv_object_name: Annotated[str, reduce_latest]
    cv_link: Annotated[str, reduce_latest]
    extracted_cv_data: Annotated[dict, reduce_latest]
    summary: Annotated[str, reduce_latest]
    timestamp: Annotated[str, reduce_latest]
    errors: Annotated[list[str], reduce_latest]
    messages: Annotated[list[AnyMessage], add_messages]
    # Optional for "My Resumes" association
    user_id: Annotated[str, reduce_latest]
    user_email: Annotated[str, reduce_latest]
    # Set by save_candidate_to_mongodb
    candidate_id: Annotated[str, reduce_latest]
    # Injected by caller for persistence node (db reference)
    _candidates_collection: Any


class JobEvaluationState(TypedDict, total=False):
    """State for Graph2: one job + one candidate (from DB). No cv_file_path."""
    # Job side
    job_id: Annotated[str, reduce_latest]
    job_title: Annotated[str, reduce_latest]
    job_description: Annotated[str, reduce_latest]
    job_description_html: Annotated[str, reduce_latest]
    hr_email: Annotated[str, reduce_latest]
    job_skills: Annotated[JobSkills, reduce_latest]
    # Candidate side (from MongoDB)
    candidate_id: Annotated[str, reduce_latest]
    candidate_name: Annotated[str, reduce_latest]
    candidate_email: Annotated[str, reduce_latest]
    summary: Annotated[str, reduce_latest]
    extracted_cv_data: Annotated[dict, reduce_latest]
    cv_link: Annotated[str, reduce_latest]
    # Outputs
    evaluation: Annotated[dict, reduce_latest]
    skills_match: Annotated[dict, reduce_latest]
    evaluation_score: Annotated[int, reduce_latest]
    tag: Annotated[str, reduce_latest]
    notification_message: Annotated[str, reduce_latest]
    notify_hr: Annotated[bool, reduce_latest]
    timestamp: Annotated[str, reduce_latest]
    errors: Annotated[list[str], reduce_latest]
    messages: Annotated[list[AnyMessage], add_messages]


# candidate_evaluations collection (option A): one doc per (candidate_id, job_id).
# Document shape: { candidate_id, job_id, score, evaluation, skills_match, tag, timestamp, ... }
