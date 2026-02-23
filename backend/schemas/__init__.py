# Pydantic schemas: auth (user/token) and hr (agent state, evaluation, etc.)
from backend.schemas.auth import (
    UserRole,
    UserBase,
    UserCreate,
    UserUpdate,
    User,
    UserInDB,
    Token,
    TokenData,
)
from backend.schemas.hr import (
    PersonalData,
    Education,
    JobHistory,
    Qualifications,
    SkillsMatch,
    CandidateEvaluation,
    JobSkills,
    CVExtractionState,
    JobEvaluationState,
    reduce_latest,
)

__all__ = [
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "User",
    "UserInDB",
    "Token",
    "TokenData",
    "PersonalData",
    "Education",
    "JobHistory",
    "Qualifications",
    "SkillsMatch",
    "CandidateEvaluation",
    "JobSkills",
    "CVExtractionState",
    "JobEvaluationState",
    "reduce_latest",
]
