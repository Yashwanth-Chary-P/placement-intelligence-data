"""
run_pipeline.py
Main entry point for the Placement Intelligence Data Pipeline.
"""
import time
import sys
from pathlib import Path

# Ensure project root is in PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts import config
from scripts.utils.logger import get_logger
from scripts.utils import validator
from scripts.extractors import notice_parser, pdf_parser
from scripts.transformers import normalizer, data_merger, student_transformer, stats_generator

logger = get_logger("pipeline_runner")

def run():
    start_time = time.time()
    logger.info("Pipeline Execution Started")
    
    # Initialize logs tracking
    stats = {
        "Start Time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)),
        "Total Notices Parsed": 0,
        "Total Placement Rows Parsed": 0,
        "Duplicate Notices": 0,
        "Invalid Placement Rows": 0,
        "Duplicate Student Records": 0,
        "Unknown Companies": 0,
        "Total Students Processed": 0,
        "Total Master Records": 0,
        "Total Company Stats Records": 0
    }
    
    # Reset CSV logs
    for log_file in [config.UNKNOWN_COMPANIES_CSV, config.DUPLICATE_STUDENTS_CSV, config.DUPLICATE_NOTICES_CSV, config.INVALID_ROWS_CSV]:
        if Path(log_file).exists():
            Path(log_file).unlink()

    # 1. Parse Notices
    notices_df = notice_parser.process_notices()
    if not notices_df.empty:
        notices_df, stats["Duplicate Notices"] = validator.validate_notices(notices_df)
        stats["Total Notices Parsed"] = len(notices_df)
        
        # Normalize companies in notices
        notices_df, unknown_notices = normalizer.normalize_dataframe(notices_df)
        stats["Unknown Companies"] += unknown_notices
        
        notices_df.to_csv(config.NOTICES_CSV, index=False)
        logger.info(f"Saved notices.csv ({len(notices_df)} rows)")

    # 2. Parse Placement Reports
    placements_df, pdf_failures = pdf_parser.process_pdfs()
    if not placements_df.empty:
        placements_df, stats["Invalid Placement Rows"], stats["Duplicate Student Records"] = validator.validate_placements(placements_df)
        stats["Total Placement Rows Parsed"] = len(placements_df)
        
        # Normalize companies in placements
        placements_df, unknown_placements = normalizer.normalize_dataframe(placements_df)
        stats["Unknown Companies"] += unknown_placements
        
        placements_df.to_csv(config.PLACEMENTS_CSV, index=False)
        logger.info(f"Saved placements.csv ({len(placements_df)} rows)")

    # 3. Generate Student Dataset
    if not placements_df.empty:
        students_df = student_transformer.generate_students_dataset(placements_df)
        stats["Total Students Processed"] = len(students_df)
        students_df.to_csv(config.STUDENTS_CSV, index=False)
        logger.info(f"Saved students.csv ({len(students_df)} rows)")

    # 4. Generate Master Dataset
    master_df = data_merger.generate_master_dataset(notices_df, placements_df)
    if not master_df.empty:
        stats["Total Master Records"] = len(master_df)
        master_df.to_csv(config.COMPANY_PLACEMENT_MASTER_CSV, index=False)
        logger.info(f"Saved company_placement_master.csv ({len(master_df)} rows)")

    # 5. Generate Company Statistics
    stats_df = stats_generator.generate_company_statistics(notices_df, placements_df)
    if not stats_df.empty:
        stats["Total Company Stats Records"] = len(stats_df)
        stats_df.to_csv(config.COMPANY_STATISTICS_CSV, index=False)
        logger.info(f"Saved company_statistics.csv ({len(stats_df)} rows)")
        
    # Finalize Validation and Data Quality Report
    finish_time = time.time()
    duration = finish_time - start_time
    stats["Finish Time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(finish_time))
    stats["Execution Duration (seconds)"] = round(duration, 2)
    stats["PDF Parse Failures"] = pdf_failures
    
    validator.generate_quality_report(stats)
    
    logger.info(f"Pipeline Execution Finished in {duration:.2f} seconds.")

if __name__ == "__main__":
    run()
