# ============================================================================
# DATA EXPORT
# ============================================================================

"""
Export candidate data to CSV and Excel formats
"""

import csv
import io
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

# Optional dependencies for Excel export
try:
    import xlsxwriter
    XLSX_SUPPORT = True
except ImportError:
    XLSX_SUPPORT = False

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataExporter:
    """
    Export candidate data to various formats
    """

    def __init__(self):
        """Initialize data exporter"""
        self.supported_formats = ["csv"]
        if XLSX_SUPPORT:
            self.supported_formats.append("xlsx")

    def export_to_csv(
        self,
        data: List[Dict[str, Any]],
        output_path: str = None,
        include_headers: bool = True
    ) -> str:
        """
        Export candidate data to CSV format

        Args:
            data: List of candidate result dictionaries
            output_path: Optional file path to save CSV
            include_headers: Whether to include column headers

        Returns:
            CSV content as string if output_path is None, else file path
        """
        if not data:
            logger.warning("No data to export")
            return ""

        # Define CSV columns
        columns = [
            "timestamp",
            "candidate_name",
            "candidate_email",
            "job_title",
            "score",
            "decision",
            "summary",
            "cv_link",
            "strengths",
            "gaps",
            "matched_skills",
            "missing_skills",
            "reasoning",
            "processing_time_seconds"
        ]

        # Prepare output
        output = io.StringIO() if output_path is None else None

        if output_path:
            file_handle = open(output_path, 'w', newline='', encoding='utf-8')
            writer = csv.writer(file_handle)
        else:
            writer = csv.writer(output)

        # Write headers
        if include_headers:
            writer.writerow(columns)

        # Write data rows
        for item in data:
            row = []

            # Extract nested data safely
            evaluation = item.get("evaluation", {})

            # Build row data
            row.append(item.get("timestamp", ""))
            row.append(item.get("candidate_name", ""))
            row.append(item.get("candidate_email", ""))
            row.append(item.get("job_title", ""))

            # Score and decision
            row.append(item.get("evaluation_score", evaluation.get("score", "")))
            row.append(evaluation.get("decision", ""))

            # Summary
            row.append(item.get("summary", ""))

            # CV Link
            row.append(item.get("cv_link", ""))

            # Strengths and gaps
            strengths = evaluation.get("strengths", [])
            gaps = evaluation.get("gaps", [])
            row.append("; ".join(strengths) if strengths else "")
            row.append("; ".join(gaps) if gaps else "")

            # Skills match
            skills_match = item.get("skills_match", {})
            row.append("; ".join(skills_match.get("strong", [])))
            row.append("; ".join(skills_match.get("missing", [])))

            # Reasoning
            row.append(evaluation.get("reasoning", ""))

            # Processing time
            row.append(item.get("processing_time_seconds", ""))

            writer.writerow(row)

        if output_path:
            file_handle.close()
            logger.info(f"Exported {len(data)} records to {output_path}")
            return output_path
        else:
            csv_content = output.getvalue()
            output.close()
            logger.info(f"Generated CSV with {len(data)} records")
            return csv_content

    def export_to_excel(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        sheet_name: str = "Candidates"
    ) -> str:
        """
        Export candidate data to Excel format with formatting

        Args:
            data: List of candidate result dictionaries
            output_path: File path to save Excel file
            sheet_name: Name of the worksheet

        Returns:
            File path to saved Excel file
        """
        if not XLSX_SUPPORT:
            raise ImportError(
                "xlsxwriter is required for Excel export. "
                "Install with: pip install xlsxwriter"
            )

        if not data:
            logger.warning("No data to export")
            return ""

        # Create workbook
        workbook = xlsxwriter.Workbook(output_path)
        worksheet = workbook.add_worksheet(sheet_name)

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        score_format = workbook.add_format({
            'num_format': '0',
            'bold': True,
            'border': 1
        })

        high_score_format = workbook.add_format({
            'num_format': '0',
            'bold': True,
            'bg_color': '#C6EFCE',  # Light green
            'font_color': '#006100',
            'border': 1
        })

        low_score_format = workbook.add_format({
            'num_format': '0',
            'bold': True,
            'bg_color': '#FFC7CE',  # Light red
            'font_color': '#9C0006',
            'border': 1
        })

        cell_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'top'
        })

        # Define columns
        columns = [
            "Timestamp",
            "Candidate Name",
            "Email",
            "Job Title",
            "Score",
            "Decision",
            "Summary",
            "CV Link",
            "Strengths",
            "Gaps",
            "Matched Skills",
            "Missing Skills",
            "Reasoning",
            "Processing Time (s)"
        ]

        # Set column widths
        column_widths = [
            20,  # Timestamp
            25,  # Candidate Name
            30,  # Email
            30,  # Job Title
            8,   # Score
            15,  # Decision
            50,  # Summary
            40,  # CV Link
            40,  # Strengths
            40,  # Gaps
            40,  # Matched Skills
            40,  # Missing Skills
            50,  # Reasoning
            18   # Processing Time
        ]

        for col, width in enumerate(column_widths):
            worksheet.set_column(col, col, width)

        # Write headers
        for col, header in enumerate(columns):
            worksheet.write(0, col, header, header_format)

        # Freeze header row
        worksheet.freeze_panes(1, 0)

        # Write data rows
        for row_idx, item in enumerate(data, start=1):
            evaluation = item.get("evaluation", {})
            skills_match = item.get("skills_match", {})

            # Extract data
            row_data = [
                item.get("timestamp", ""),
                item.get("candidate_name", ""),
                item.get("candidate_email", ""),
                item.get("job_title", ""),
                item.get("evaluation_score", evaluation.get("score", "")),
                evaluation.get("decision", ""),
                item.get("summary", ""),
                item.get("cv_link", ""),
                "; ".join(evaluation.get("strengths", [])),
                "; ".join(evaluation.get("gaps", [])),
                "; ".join(skills_match.get("strong", [])),
                "; ".join(skills_match.get("missing", [])),
                evaluation.get("reasoning", ""),
                item.get("processing_time_seconds", "")
            ]

            # Write cells with appropriate formatting
            for col, value in enumerate(row_data):
                if col == 4:  # Score column
                    score = value if isinstance(value, (int, float)) else 0
                    if score >= 70:
                        worksheet.write(row_idx, col, score, high_score_format)
                    elif score < 50:
                        worksheet.write(row_idx, col, score, low_score_format)
                    else:
                        worksheet.write(row_idx, col, score, score_format)
                else:
                    worksheet.write(row_idx, col, value, cell_format)

        # Add summary sheet
        self._add_summary_sheet(workbook, data)

        workbook.close()
        logger.info(f"Exported {len(data)} records to {output_path}")
        return output_path

    def _add_summary_sheet(self, workbook, data: List[Dict[str, Any]]):
        """Add summary statistics sheet to Excel workbook"""
        summary_sheet = workbook.add_worksheet("Summary")

        # Calculate statistics
        total_candidates = len(data)
        successful = [d for d in data if d.get("success", True)]
        scores = [
            d.get("evaluation_score", 0)
            for d in successful
            if isinstance(d.get("evaluation_score"), (int, float))
        ]

        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            high_scorers = len([s for s in scores if s >= 70])
            low_scorers = len([s for s in scores if s < 50])
        else:
            avg_score = max_score = min_score = high_scorers = low_scorers = 0

        # Write summary
        summary_data = [
            ["Total Candidates", total_candidates],
            ["Successful Evaluations", len(successful)],
            ["", ""],
            ["Average Score", f"{avg_score:.1f}"],
            ["Highest Score", max_score],
            ["Lowest Score", min_score],
            ["", ""],
            ["High Scorers (>=70)", high_scorers],
            ["Low Scorers (<50)", low_scorers],
            ["Mid Range (50-69)", len(scores) - high_scorers - low_scorers],
        ]

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white'
        })

        cell_format = workbook.add_format({
            'border': 1
        })

        summary_sheet.set_column(0, 0, 30)
        summary_sheet.set_column(1, 1, 20)

        for row_idx, (label, value) in enumerate(summary_data):
            if label:
                summary_sheet.write(row_idx, 0, label, header_format)
                summary_sheet.write(row_idx, 1, value, cell_format)

    def export_batch_results(
        self,
        batch_result: Dict[str, Any],
        format: str = "csv",
        output_dir: str = "./exports"
    ) -> Dict[str, str]:
        """
        Export batch processing results to file

        Args:
            batch_result: Batch processing result dictionary
            format: Export format ('csv' or 'xlsx')
            output_dir: Directory to save export files

        Returns:
            Dictionary with file paths
        """
        if format not in self.supported_formats:
            raise ValueError(f"Unsupported format: {format}. Use: {self.supported_formats}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        batch_id = batch_result.get("batch_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Extract results from batch
        results = batch_result.get("results", [])

        export_files = {}

        if format == "csv":
            filename = f"batch_{batch_id}_{timestamp}.csv"
            file_path = output_path / filename

            self.export_to_csv(results, str(file_path))
            export_files["csv"] = str(file_path)

        elif format == "xlsx":
            filename = f"batch_{batch_id}_{timestamp}.xlsx"
            file_path = output_path / filename

            self.export_to_excel(results, str(file_path))
            export_files["excel"] = str(file_path)

        # Export summary statistics
        summary_file = output_path / f"summary_{batch_id}_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(f"Batch ID: {batch_id}\n")
            f.write(f"Timestamp: {batch_result.get('completed_at', 'N/A')}\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"Total Candidates: {batch_result.get('total_candidates', 0)}\n")
            f.write(f"Successful: {batch_result.get('successful', 0)}\n")
            f.write(f"Failed: {batch_result.get('failed', 0)}\n")
            f.write(f"Average Score: {batch_result.get('average_score', 0):.1f}\n")
            f.write(f"Highest Score: {batch_result.get('highest_score', 0)}\n")
            f.write(f"Lowest Score: {batch_result.get('lowest_score', 0)}\n")
            f.write(f"Total Processing Time: {batch_result.get('total_processing_time_seconds', 0):.1f}s\n")
            f.write(f"Average Processing Time: {batch_result.get('average_processing_time_seconds', 0):.1f}s\n")

        export_files["summary"] = str(summary_file)

        logger.info(f"Exported batch results to: {export_files}")
        return export_files


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def export_candidates_to_csv(data: List[Dict[str, Any]], output_path: str = None) -> str:
    """
    Convenience function to export candidates to CSV

    Args:
        data: List of candidate result dictionaries
        output_path: Optional file path

    Returns:
        CSV content or file path
    """
    exporter = DataExporter()
    return exporter.export_to_csv(data, output_path)


def export_candidates_to_excel(data: List[Dict[str, Any]], output_path: str) -> str:
    """
    Convenience function to export candidates to Excel

    Args:
        data: List of candidate result dictionaries
        output_path: File path for Excel file

    Returns:
        File path
    """
    exporter = DataExporter()
    return exporter.export_to_excel(data, output_path)


def export_batch_to_file(
    batch_result: Dict[str, Any],
    format: str = "csv",
    output_dir: str = "./exports"
) -> Dict[str, str]:
    """
    Convenience function to export batch results

    Args:
        batch_result: Batch processing result
        format: Export format ('csv' or 'xlsx')
        output_dir: Output directory

    Returns:
        Dictionary with file paths
    """
    exporter = DataExporter()
    return exporter.export_batch_results(batch_result, format, output_dir)
