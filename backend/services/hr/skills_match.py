"""
Skills Matching Module

Matches job requirements with candidate skills
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def map_job_to_candidate_skills(
    job_required_skills: List[str],
    candidate_skills: List[str]
) -> Dict[str, Any]:
    """
    Match candidate skills with job requirements

    Args:
        job_required_skills: List of skills required for the job
        candidate_skills: List of candidate's skills

    Returns:
        Dictionary containing:
            - matched_skills: Skills that match
            - missing_skills: Required skills not found in candidate
            - match_percentage: Percentage of skills matched
            - match_score: Weighted score considering skill importance
    """

    # Normalize skills to lowercase for comparison
    job_skills_normalized = [skill.lower().strip() for skill in job_required_skills]
    candidate_skills_normalized = [skill.lower().strip() for skill in candidate_skills]

    # Find matched skills
    matched_skills = []
    missing_skills = []

    for job_skill in job_required_skills:
        job_skill_lower = job_skill.lower().strip()

        # Check for exact match
        if job_skill_lower in candidate_skills_normalized:
            matched_skills.append(job_skill)
        else:
            # Check for partial match (e.g., "Python" matches "Python 3")
            partial_match = False
            for candidate_skill in candidate_skills:
                if job_skill_lower in candidate_skill.lower() or candidate_skill.lower() in job_skill_lower:
                    matched_skills.append(job_skill)
                    partial_match = True
                    break

            if not partial_match:
                missing_skills.append(job_skill)

    # Calculate match percentage
    total_required = len(job_required_skills)
    match_count = len(matched_skills)
    match_percentage = (match_count / total_required * 100) if total_required > 0 else 0

    # Calculate match score (0-100)
    # Weight: 70% for matched skills, 30% for skill count
    match_score = min(100, match_percentage)

    result = {
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_percentage": round(match_percentage, 2),
        "match_score": round(match_score, 2),
        "total_required_skills": total_required,
        "total_candidate_skills": len(candidate_skills)
    }

    logger.info(f"Skills matching complete: {match_percentage:.2f}% match")

    return result


def assess_skill_level(
    skill: str,
    candidate_experience: List[Dict[str, Any]]
) -> str:
    """
    Assess candidate's proficiency level for a specific skill based on experience

    Args:
        skill: Skill to assess
        candidate_experience: List of candidate's work experience

    Returns:
        Proficiency level: 'beginner', 'intermediate', 'advanced', or 'expert'
    """

    # Count how many times the skill appears in experience
    skill_mentions = 0
    years_of_experience = 0

    for exp in candidate_experience:
        description = exp.get("description", "").lower()
        title = exp.get("title", "").lower()

        if skill.lower() in description or skill.lower() in title:
            skill_mentions += 1

            # Estimate years from duration if available
            duration = exp.get("duration", "")
            if "year" in duration.lower():
                try:
                    years = int(''.join(filter(str.isdigit, duration.split()[0])))
                    years_of_experience += years
                except (ValueError, IndexError):
                    pass

    # Determine level based on mentions and experience
    if skill_mentions >= 3 or years_of_experience >= 5:
        return "expert"
    elif skill_mentions >= 2 or years_of_experience >= 3:
        return "advanced"
    elif skill_mentions >= 1 or years_of_experience >= 1:
        return "intermediate"
    else:
        return "beginner"


def rank_candidates_by_skills(
    candidates: List[Dict[str, Any]],
    job_required_skills: List[str]
) -> List[Dict[str, Any]]:
    """
    Rank candidates based on their skills match score

    Args:
        candidates: List of candidates with their skills
        job_required_skills: Required skills for the job

    Returns:
        List of candidates sorted by match score (highest first)
    """

    ranked_candidates = []

    for candidate in candidates:
        candidate_skills = candidate.get("skills", {}).get("technical_skills", [])

        # Calculate match score
        match_result = map_job_to_candidate_skills(
            job_required_skills,
            candidate_skills
        )

        # Add match info to candidate
        candidate_with_score = {
            **candidate,
            "skills_match": match_result,
            "rank_score": match_result["match_score"]
        }

        ranked_candidates.append(candidate_with_score)

    # Sort by rank score descending
    ranked_candidates.sort(key=lambda x: x["rank_score"], reverse=True)

    # Add rank position
    for idx, candidate in enumerate(ranked_candidates, 1):
        candidate["rank"] = idx

    return ranked_candidates
