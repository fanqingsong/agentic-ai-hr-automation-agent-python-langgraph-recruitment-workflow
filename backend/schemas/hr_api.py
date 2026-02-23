# ============================================================================
# HR API REQUEST/RESPONSE MODELS (MongoDB, camelCase)
# ============================================================================

from typing import Dict, Any, List, Optional
from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field, model_validator, ConfigDict, field_serializer, field_validator
from pydantic.alias_generators import to_camel
from bs4 import BeautifulSoup
import re

from backend.utils.ulid_helper import generate_ulid


class ProcessingResult(BaseModel):
    """Model for processing result response"""
    success: bool
    message: str
    candidate_name: str
    candidate_email: str
    summary: str
    score: int
    reasoning: str
    cv_link: str
    timestamp: str
    errors: List[str] = []


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    service: str
    version: str = "1.0.0"
    config: Dict[str, str]


class HRUserResponse(BaseModel):
    """User model for HR API (MongoDB response)"""
    id: str
    name: str
    email: str
    role: Optional[str] = "hr manager"

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

    @field_serializer('id')
    def serialize_id(self, value: Optional[str]) -> Optional[str]:
        if value and isinstance(value, ObjectId):
            return str(value)
        return value


class JobApplication(BaseModel):
    """Job application (title + description)"""
    title: str
    description_html: str = Field(
        validation_alias="descriptionHTML",
        serialization_alias="descriptionHTML"
    )
    description: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

    @model_validator(mode='after')
    def strip_html_and_assign(self) -> 'JobApplication':
        if self.description_html:
            soup = BeautifulSoup(self.description_html, "html.parser")
            block_elements = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                              'ul', 'ol', 'blockquote', 'pre', 'hr']
            for tag in soup.find_all(block_elements):
                tag.insert_before('\n\n')
                tag.insert_after('\n\n')
            for li in soup.find_all('li'):
                li.insert_before('\n• ')
            for br in soup.find_all('br'):
                br.replace_with('\n')
            text = soup.get_text()
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = '\n'.join(line.strip() for line in text.split('\n'))
            text = text.strip()
            self.description = text
        return self


class HRJobPost(BaseModel):
    """HR job post (MongoDB document)"""
    id: Optional[str] = Field(
        default=None,
        validation_alias="_id",
        serialization_alias="id"
    )
    ulid: Optional[str] = Field(default_factory=generate_ulid)
    job_application: JobApplication = Field(
        validation_alias="jobApplication",
        serialization_alias="jobApplication"
    )
    hr: HRUserResponse
    created_at: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

    @field_serializer('id')
    def serialize_id(self, value: Optional[str]) -> Optional[str]:
        if value and isinstance(value, ObjectId):
            return str(value)
        return value

    @field_validator('ulid', mode='before')
    @classmethod
    def generate_ulid_if_missing(cls, v):
        if v is None or v == '':
            return generate_ulid()
        return v


class CandidateSubmittedApplication(BaseModel):
    """Candidate submission payload"""
    job_id: str = Field(
        validation_alias="jobId",
        serialization_alias="jobId"
    )
    name: str
    email: EmailStr

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )


# Alias for compatibility (dashboard and hr_automation use HRUser)
HRUser = HRUserResponse
