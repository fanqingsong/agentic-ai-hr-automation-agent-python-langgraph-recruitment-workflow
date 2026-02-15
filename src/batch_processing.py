# ============================================================================
# BATCH PROCESSING
# ============================================================================

"""
Batch processing module for handling multiple CV submissions concurrently
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

from src.hr_automation import process_candidate
from src.fastapi_api import HRJobPost
from src.data_models import AgentState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Handles batch processing of multiple candidate applications
    """

    def __init__(self, max_concurrent: int = 5):
        """
        Initialize batch processor

        Args:
            max_concurrent: Maximum number of concurrent processing tasks
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_single_candidate(
        self,
        candidate_data: Dict[str, Any],
        hr_job_post: HRJobPost,
        batch_id: str = None
    ) -> Dict[str, Any]:
        """
        Process a single candidate with semaphore control

        Args:
            candidate_data: Candidate information dict
            hr_job_post: Job posting details
            batch_id: Optional batch identifier for tracking

        Returns:
            Processing result with metadata
        """
        async with self.semaphore:
            try:
                start_time = datetime.now()
                logger.info(f"Processing candidate: {candidate_data.get('name')}")

                # Process the candidate
                result = await process_candidate(candidate_data, hr_job_post)

                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds()

                return {
                    "success": True,
                    "batch_id": batch_id,
                    "candidate_name": result.get("candidate_name"),
                    "candidate_email": result.get("candidate_email"),
                    "score": result.get("evaluation_score"),
                    "processing_time_seconds": processing_time,
                    "timestamp": end_time.isoformat(),
                    "result": result,
                    "errors": result.get("errors", [])
                }

            except Exception as e:
                logger.error(f"Error processing candidate {candidate_data.get('name')}: {str(e)}")
                return {
                    "success": False,
                    "batch_id": batch_id,
                    "candidate_name": candidate_data.get("name"),
                    "candidate_email": candidate_data.get("email"),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

    async def process_batch(
        self,
        candidates: List[Dict[str, Any]],
        hr_job_post: HRJobPost,
        batch_id: str = None
    ) -> Dict[str, Any]:
        """
        Process multiple candidates concurrently

        Args:
            candidates: List of candidate data dictionaries
            hr_job_post: Job posting details
            batch_id: Optional batch identifier

        Returns:
            Batch processing summary with individual results
        """
        if not batch_id:
            from src.utils.ulid_helper import generate_ulid
            batch_id = generate_ulid()

        batch_start_time = datetime.now()
        logger.info(f"Starting batch {batch_id} with {len(candidates)} candidates")

        # Create tasks for all candidates
        tasks = [
            self.process_single_candidate(candidate, hr_job_post, batch_id)
            for candidate in candidates
        ]

        # Execute concurrently with semaphore control
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate statistics
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        total_processing_time = (datetime.now() - batch_start_time).total_seconds()

        # Collect scores
        scores = [
            r.get("score")
            for r in results
            if isinstance(r, dict) and r.get("success")
        ]

        batch_summary = {
            "batch_id": batch_id,
            "total_candidates": len(candidates),
            "successful": successful,
            "failed": failed,
            "total_processing_time_seconds": total_processing_time,
            "average_processing_time_seconds": total_processing_time / len(candidates),
            "average_score": sum(scores) / len(scores) if scores else 0,
            "highest_score": max(scores) if scores else 0,
            "lowest_score": min(scores) if scores else 0,
            "started_at": batch_start_time.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "results": results
        }

        logger.info(
            f"Batch {batch_id} completed: "
            f"{successful}/{len(candidates)} successful, "
            f"avg score: {batch_summary['average_score']:.1f}"
        )

        return batch_summary


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def process_candidates_batch(
    candidates: List[Dict[str, Any]],
    hr_job_post: HRJobPost,
    max_concurrent: int = 5
) -> Dict[str, Any]:
    """
    Convenience function for batch processing

    Args:
        candidates: List of candidate dictionaries with keys:
                    - name: str
                    - email: str
                    - cv_file_path: str
        hr_job_post: Job posting details
        max_concurrent: Maximum concurrent processing (default: 5)

    Returns:
        Batch processing summary
    """
    processor = BatchProcessor(max_concurrent=max_concurrent)
    return await processor.process_batch(candidates, hr_job_post)


async def process_candidates_from_directory(
    cv_directory: str,
    hr_job_post: HRJobPost,
    max_concurrent: int = 5
) -> Dict[str, Any]:
    """
    Process all CVs from a directory

    Args:
        cv_directory: Path to directory containing CV PDF files
        hr_job_post: Job posting details
        max_concurrent: Maximum concurrent processing

    Returns:
        Batch processing summary
    """
    cv_dir = Path(cv_directory)

    if not cv_dir.exists():
        raise ValueError(f"Directory not found: {cv_directory}")

    # Find all PDF files
    cv_files = list(cv_dir.glob("*.pdf")) + list(cv_dir.glob("*.PDF"))

    if not cv_files:
        raise ValueError(f"No PDF files found in {cv_directory}")

    # Create candidate list from filenames
    candidates = []
    for cv_path in cv_files:
        # Extract name from filename (remove extension)
        name = cv_path.stem.replace("_", " ").replace("-", " ")

        candidates.append({
            "name": name,
            "email": f"{name.lower().replace(' ', '.')}@example.com",  # Placeholder
            "cv_file_path": str(cv_path)
        })

    logger.info(f"Found {len(candidates)} CV files in {cv_directory}")

    processor = BatchProcessor(max_concurrent=max_concurrent)
    return await processor.process_batch(candidates, hr_job_post)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def example_batch_processing():
        """Example of batch processing"""

        # Example job posting
        from src.fastapi_api import JobApplication, HRUser

        job_application = JobApplication(
            title="Senior AI Engineer",
            description="We are looking for a Senior AI Engineer...",
            description_html=""
        )

        hr_user = HRUser(
            id="1",
            name="HR Manager",
            email="hr@company.com"
        )

        hr_job_post = HRJobPost(
            id=1,
            ulid="job_001",
            job_application=job_application,
            hr=hr_user
        )

        # Example 1: Process specific candidates
        candidates = [
            {
                "name": "John Doe",
                "email": "john.doe@email.com",
                "cv_file_path": "/path/to/john_resume.pdf"
            },
            {
                "name": "Jane Smith",
                "email": "jane.smith@email.com",
                "cv_file_path": "/path/to/jane_resume.pdf"
            },
            {
                "name": "Bob Johnson",
                "email": "bob.johnson@email.com",
                "cv_file_path": "/path/to/bob_resume.pdf"
            }
        ]

        # Process batch
        result = await process_candidates_batch(
            candidates=candidates,
            hr_job_post=hr_job_post,
            max_concurrent=3
        )

        print(f"Batch ID: {result['batch_id']}")
        print(f"Successful: {result['successful']}/{result['total_candidates']}")
        print(f"Average Score: {result['average_score']:.1f}")
        print(f"Total Time: {result['total_processing_time_seconds']:.1f}s")

        # Example 2: Process all CVs from directory
        # result = await process_candidates_from_directory(
        #     cv_directory="./resumes",
        #     hr_job_post=hr_job_post,
        #     max_concurrent=5
        # )

    # Run example
    # asyncio.run(example_batch_processing())
