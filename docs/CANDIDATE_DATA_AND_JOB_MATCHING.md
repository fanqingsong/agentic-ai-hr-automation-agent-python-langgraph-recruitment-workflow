# Candidate Data Extraction and Job Matching

This document describes the current runtime implementation of candidate data
extraction, persistence, and job-description matching. It is intended to
document the code as implemented, including current limitations.

Last reviewed: 2026-08-11

## 1. Candidate Data Extraction

### Inputs

Candidate data comes from two sources:

1. Request metadata supplies the top-level candidate name and email.
   - Single CV uploads use the submitted form values.
   - Batch uploads initially derive the name from the file name and may use an
     `@example.com` placeholder email.
2. The CV file supplies the structured profile extracted by the LLM.

The supported CV formats are PDF, DOC, and DOCX at the API boundary. PDF text
is read with PyPDF2 and Word text is read with python-docx. The extracted text
is truncated to 12,000 characters before it is sent to the LLM.

Relevant code:

- `backend/api/routes/cv.py`
- `backend/api/routes/batch.py`
- `backend/services/hr/data_extraction.py`

### CV extraction workflow

The first LangGraph workflow is defined in
`backend/services/hr/graph/cv_extraction_workflow.py`:

```text
upload_cv
  -> extract_cv_data_node
  -> generate_summary
  -> save_candidate_to_mongodb
  -> END
```

`extract_cv_data()` creates a `JsonOutputParser` backed by the `CVExtraction`
Pydantic schema. The structured result has the following shape:

```json
{
  "personal_info": {
    "name": "string",
    "email": "string",
    "phone": "string",
    "location": "string",
    "linkedin": "string",
    "portfolio": "string"
  },
  "experience": [
    {
      "title": "string",
      "company": "string",
      "duration": "string",
      "description": "string"
    }
  ],
  "education": [
    {
      "degree": "string",
      "institution": "string",
      "year": "string"
    }
  ],
  "skills": {
    "technical_skills": ["string"],
    "soft_skills": ["string"],
    "tools": ["string"]
  }
}
```

The extraction models are defined in
`backend/services/hr/data_extraction.py`. If no CV text can be read, the
service returns mock extraction data. If the LLM extraction fails, the
fallback logic attempts to extract basic identity fields with regular
expressions.

The summary node does not call an LLM. It creates a short template-based
summary from the extracted name, skills, and number of experience entries.

### Candidate persistence

`save_candidate_to_mongodb()` in
`backend/services/hr/graph/nodes/persistence.py` inserts the candidate into the
MongoDB `candidates` collection. A candidate document contains:

```json
{
  "candidate_name": "string",
  "candidate_email": "string",
  "cv_file_url": "string",
  "cv_object_name": "string",
  "cv_link": "string",
  "extracted_cv_data": {},
  "summary": "string",
  "timestamp": "YYYY-MM-DD HH:MM:SS",
  "errors": []
}
```

Authenticated requests may also store `user_id` and `user_email`.

The original CV is stored in MinIO under the `cvs/` prefix, or in the
configured local fallback storage. MongoDB stores the resulting object name
and URL rather than the binary CV itself.

For batch imports, `backend/services/hr/batch_processing.py` performs
additional updates:

- associates the candidate with a `batch_id`;
- stores `file_hash` and `source_folder`;
- uses SHA-256 hashes for duplicate detection;
- replaces file-name-derived identities and placeholder emails with values
  from `extracted_cv_data.personal_info` when available.

## 2. Job Description Matching

### Evaluation workflow

The second LangGraph workflow is defined in
`backend/services/hr/graph/job_evaluation_workflow.py`:

```text
extract_job_skills_node
  -> evaluate
  -> skills_match
  -> score_decision
  -> END
```

The service entry points are in `backend/services/hr/automation.py`. Evaluation
can run for one candidate and one job, all candidates for a job, or all jobs
for a candidate.

### Job skill extraction

`extract_job_skills_node` reads the plain-text `job_description` and asks an
LLM to return:

```json
{
  "tech_skills": ["string"],
  "soft_skills": ["string"]
}
```

The result uses the `JobSkills` schema in `backend/schemas/hr.py`. Extracted
skills are cached in `hr_job_posts.job_skills`, so a batch evaluation does not
need to extract the same job skills for every candidate.

The HTML job description is not used by the evaluator.

### Evaluation score

`evaluate_candidate_node` in
`backend/services/hr/graph/nodes/evaluation.py` sends only these two values to
the evaluation LLM:

```text
Candidate Summary:
{summary}

Job Description:
{job_description}
```

The LLM returns a `CandidateEvaluation` object:

```json
{
  "score": 85,
  "reasoning": "string",
  "strengths": ["string"],
  "gaps": ["string"],
  "decision": "hire"
}
```

The score must be between 1 and 100. There is currently no deterministic
weighting formula for skills, experience, education, or other candidate
attributes. The final score is the score produced directly by the LLM.

Although `extracted_cv_data` and extracted job skills are present in the graph
state, they are not included in the evaluation prompt. Consequently, the
quality of the template-generated candidate summary directly affects the
score. Evaluation parsing failures fall back to a regular-expression parser
or a neutral score of 50.

### Skill matching

After the LLM has already produced the score, `skills_match_node` independently
compares:

- candidate `technical_skills` plus `tools`; and
- job `tech_skills`.

Matching is case-insensitive exact string equality. The result is:

```json
{
  "strong": ["Python"],
  "partial": [],
  "missing": ["FastAPI"]
}
```

Current behavior and limitations:

- skill matching does not modify the LLM score;
- partial matches are not calculated and are always empty;
- soft skills are not compared;
- aliases, synonyms, proficiency, and years of experience are not considered;
- `backend/services/hr/skills_match.py` contains richer matching helpers, but
  that module is not connected to the runtime LangGraph workflow.

### Score classification

`score_decision_node` classifies the LLM score with fixed thresholds:

```text
score >= 70       -> high_potential
50 <= score < 70  -> moderate
score < 50        -> low_potential
```

The LLM's free-text `evaluation.decision` and the threshold-based `tag` are
stored separately and are not checked for consistency. The node can set
`notify_hr`, but notification nodes are not currently connected to this
workflow.

### Evaluation persistence

Evaluations are upserted into the MongoDB `candidate_evaluations` collection
using `(candidate_id, job_id)` as the logical unique key:

```json
{
  "candidate_id": "string",
  "job_id": "string",
  "score": 85,
  "evaluation": {
    "score": 85,
    "reasoning": "string",
    "strengths": [],
    "gaps": [],
    "decision": "hire"
  },
  "skills_match": {
    "strong": [],
    "partial": [],
    "missing": []
  },
  "tag": "high_potential",
  "timestamp": "YYYY-MM-DD HH:MM:SS"
}
```

Job recommendation and job-specific export paths read from
`candidate_evaluations` and join candidate or job documents as needed.

The evaluation workflow does not write `evaluation_score` back to the
`candidates` collection. Any API path that queries
`candidates.evaluation_score` is therefore inconsistent with the current
persistence model and should instead read from `candidate_evaluations`.

## 3. Implementation Summary

Candidate extraction is schema-driven: CV text is converted to structured JSON
and stored under `candidates.extracted_cv_data`, while the original file is
stored in MinIO or local storage.

Job matching is currently LLM-driven: the LLM directly scores the
template-based candidate summary against the plain-text job description.
Technical skill matching is stored as supporting information but does not
contribute to the score.
