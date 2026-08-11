# ============================================================================
# Chunking: split candidate/job structured data into semantic units for the
# vector store. Each chunk becomes one Qdrant point instead of embedding an
# entire CV/JD as a single vector, so retrieval can target a specific
# experience entry, education entry, or job requirement section.
# ============================================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Chunk:
    """A single semantic unit to embed and index."""
    chunk_type: str
    text: str
    source_ref: Dict[str, Any] = field(default_factory=dict)


def candidate_to_chunks(extracted_cv_data: Optional[Dict[str, Any]], summary: str) -> List[Chunk]:
    """Turn a candidate's extracted CV data + summary into embeddable chunks.

    chunk_type values: "summary" | "experience" | "education" | "skills"
    """
    chunks: List[Chunk] = []
    data = extracted_cv_data or {}

    if summary:
        chunks.append(Chunk(chunk_type="summary", text=summary))

    for idx, exp in enumerate(data.get("experience", []) or []):
        title = exp.get("title", "")
        company = exp.get("company", "")
        duration = exp.get("duration", "")
        description = exp.get("description", "")
        text = f"{title} at {company} ({duration}). {description}".strip()
        if text:
            chunks.append(Chunk(chunk_type="experience", text=text, source_ref={"experience_idx": idx}))

    for idx, edu in enumerate(data.get("education", []) or []):
        degree = edu.get("degree", "")
        institution = edu.get("institution", "")
        year = edu.get("year", "")
        text = f"{degree}, {institution} ({year})".strip(", ")
        if text:
            chunks.append(Chunk(chunk_type="education", text=text, source_ref={"education_idx": idx}))

    skills = data.get("skills", {}) or {}
    skill_terms = (
        (skills.get("technical_skills") or [])
        + (skills.get("tools") or [])
        + (skills.get("soft_skills") or [])
    )
    if skill_terms:
        chunks.append(Chunk(chunk_type="skills", text=", ".join(skill_terms)))

    return chunks


def job_to_chunks(job_description: str) -> List[Chunk]:
    """Split a plain-text job description into paragraph-sized chunks.

    chunk_type values: "description" (whole JD, kept short) | "requirement_section"
    """
    chunks: List[Chunk] = []
    description = (job_description or "").strip()
    if not description:
        return chunks

    paragraphs = [p.strip() for p in description.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        chunks.append(Chunk(chunk_type="description", text=description[:2000]))
        return chunks

    for idx, para in enumerate(paragraphs):
        chunks.append(Chunk(chunk_type="requirement_section", text=para[:2000], source_ref={"section_idx": idx}))

    return chunks
