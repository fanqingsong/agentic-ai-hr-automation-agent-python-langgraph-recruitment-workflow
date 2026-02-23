"""
CV Data Extraction using project LLM (OpenAI / Azure / Anthropic / Ollama).

Extracts structured data from CV files (PDF, DOCX) by:
1. Converting the document to plain text
2. Using the configured LLM with a structured prompt to produce JSON matching CVExtraction schema
"""

from backend.config import Config
from backend.services.llm_provider import LLMFactory
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional, List

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Simple patterns for fallback when LLM is unavailable
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


# ============================================================================
# PYDANTIC MODELS FOR EXTRACTION
# ============================================================================

class PersonalInfo(BaseModel):
    """Personal information extracted from CV"""
    name: str = Field(description="Full name of the candidate")
    email: str = Field(description="Email address")
    phone: Optional[str] = Field(default="", description="Phone number")
    location: Optional[str] = Field(default="", description="City, Country")
    linkedin: Optional[str] = Field(default="", description="LinkedIn profile URL")
    portfolio: Optional[str] = Field(default="", description="Portfolio/Website URL")


class WorkExperience(BaseModel):
    """Work experience entry"""
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    duration: str = Field(description="Duration (e.g., 'Jan 2020 - Present')")
    description: Optional[str] = Field(default="", description="Job description")


class Education(BaseModel):
    """Education entry"""
    degree: str = Field(description="Degree obtained")
    institution: str = Field(description="University/School name")
    year: Optional[str] = Field(default="", description="Graduation year")


class Skills(BaseModel):
    """Skills extracted from CV"""
    technical_skills: List[str] = Field(default_factory=list, description="Technical/Programming skills")
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills")
    tools: List[str] = Field(default_factory=list, description="Tools and frameworks")


class CVExtraction(BaseModel):
    """Complete CV extraction result"""
    personal_info: PersonalInfo
    experience: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: Skills


# ============================================================================
# DOCUMENT TO TEXT
# ============================================================================

def _pdf_to_text(file_path: str) -> str:
    """Extract text from a PDF file using PyPDF2."""
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts) or ""


def _docx_to_text(file_path: str) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "DOCX support requires python-docx. Install with: pip install python-docx (or rebuild the Docker image)."
        )
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs) or ""


def _file_to_text(cv_file_path: str) -> str:
    """
    Convert a CV file (PDF or DOCX) to plain text.

    Args:
        cv_file_path: Path to the file.

    Returns:
        Extracted text content.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported.
    """
    path = Path(cv_file_path)
    if not path.exists():
        raise FileNotFoundError(f"CV file not found: {cv_file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_to_text(cv_file_path)
    if suffix in (".docx", ".doc"):
        return _docx_to_text(cv_file_path)

    raise ValueError(f"Unsupported CV file format: {suffix}. Use PDF or DOCX.")


# ============================================================================
# LLM-BASED EXTRACTION
# ============================================================================

CV_EXTRACTION_SYSTEM = """You are an expert at extracting structured information from resumes/CVs.

Extract the following from the CV text and return valid JSON only (no markdown, no code block wrapper):
- personal_info: object with name, email, phone (or ""), location (or ""), linkedin (or ""), portfolio (or "")
- experience: array of objects, each with title, company, duration, description (or "")
- education: array of objects, each with degree, institution, year (or "")
- skills: object with technical_skills (array), soft_skills (array), tools (array)

Use empty string "" for missing optional fields. Use empty arrays [] when none found."""


async def extract_cv_data(cv_file_path: str) -> dict:
    """
    Extract structured data from CV using the project's configured LLM.

    Converts the document to text (PDF/DOCX), then uses the LLM to produce
    structured data matching the CVExtraction schema. No LlamaCloud API key required.

    Args:
        cv_file_path: Path to the CV file (PDF or DOCX).

    Returns:
        Dictionary with keys: personal_info, experience, education, skills.
    """
    logger.info(f"Extracting data from CV: {cv_file_path}")

    try:
        text = _file_to_text(cv_file_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"CV file error: {e}")
        return _get_mock_extraction(cv_file_path)

    if not text or not text.strip():
        logger.warning("CV file produced no text. Returning mock data.")
        return _get_mock_extraction(cv_file_path)

    try:
        llm = LLMFactory.create_llm(
            provider=Config.LLM_PROVIDER,
            temperature=Config.EXTRACTION_TEMP,
            max_tokens=2000,
        )
        parser = JsonOutputParser(pydantic_object=CVExtraction)
        prompt = ChatPromptTemplate.from_messages([
            ("system", CV_EXTRACTION_SYSTEM + "\n\n{format_instructions}"),
            ("human", "CV text:\n\n{cv_text}"),
        ])

        chain = prompt | llm | parser
        result = await chain.ainvoke({
            "cv_text": text[:12000],  # cap length to avoid token limits
            "format_instructions": parser.get_format_instructions(),
        })

        if isinstance(result, dict):
            data = result
        else:
            data = result.model_dump() if hasattr(result, "model_dump") else dict(result)

        return {
            "personal_info": data.get("personal_info", {}),
            "experience": data.get("experience", []),
            "education": data.get("education", []),
            "skills": data.get("skills", {}),
        }
    except Exception as e:
        logger.error(f"CV extraction failed: {e}")
        return _get_fallback_extraction(cv_file_path, text)


def _extract_name_email_from_text(text: str) -> tuple:
    """Extract a plausible name (first non-empty line) and first email from text. Returns (name, email)."""
    name, email = "", ""
    if not text or not text.strip():
        return name, email
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        # First line often is the candidate name
        name = lines[0][:200].strip()
    match = EMAIL_PATTERN.search(text)
    if match:
        email = match.group(0)
    return name, email


def _get_fallback_extraction(cv_file_path: str, text: str = "") -> dict:
    """
    Fallback when LLM extraction fails: use regex to get name/email from text if available,
    otherwise return minimal placeholder so the pipeline can continue.
    """
    name, email = _extract_name_email_from_text(text)
    if not name:
        name = "Unknown Candidate"
    if not email:
        email = "unknown@example.com"
    return {
        "personal_info": {
            "name": name,
            "email": email,
            "phone": "",
            "location": "",
            "linkedin": "",
            "portfolio": "",
        },
        "experience": [],
        "education": [],
        "skills": {
            "technical_skills": [],
            "soft_skills": [],
            "tools": [],
        },
    }


def _get_mock_extraction(cv_file_path: str) -> dict:
    """
    Return mock extraction data for development/testing or when extraction fails.
    """
    return {
        "personal_info": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-234-567-8900",
            "location": "San Francisco, CA",
            "linkedin": "https://linkedin.com/in/johndoe",
            "portfolio": "https://johndoe.dev"
        },
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "duration": "2020 - Present",
                "description": "Led development of cloud-native applications"
            }
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "University of California",
                "year": "2019"
            }
        ],
        "skills": {
            "technical_skills": ["Python", "FastAPI", "Docker", "Kubernetes"],
            "soft_skills": ["Leadership", "Communication"],
            "tools": ["Git", "Jira", "AWS"]
        }
    }
