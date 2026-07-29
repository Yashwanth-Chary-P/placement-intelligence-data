"""
run_pipeline.py
Main entry point for the Placement Intelligence Data Pipeline.
"""
import time
import sys
import json
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts import config
from scripts.utils.logger import get_logger
from scripts.utils import validator
from scripts.extractors import notice_parser, pdf_parser
from scripts.transformers import cleaner, normalizer, data_merger, student_transformer, stats_generator

logger = get_logger("pipeline_runner")

def run():
    start_time = time.time()
    logger.info("Pipeline Execution Started")
    
    # Initialize logs tracking
    stats = {
        "Total Notices": 0,
        "Total Placement Records": 0,
        "Duplicate Notices": 0,
        "Invalid Placement Rows": 0,
        "Duplicate Student Records": 0,
        "Unknown Companies": 0,
        "Total Students Processed": 0,
        "Total Master Records": 0,
        "Total Company Stats Records": 0
    }
    
    # Reset CSV logs
    log_files = [
        config.UNKNOWN_COMPANIES_CSV, config.DUPLICATE_STUDENTS_CSV, 
        config.DUPLICATE_NOTICES_CSV, config.INVALID_ROWS_CSV,
        config.COMPANY_NORMALIZATION_AUDIT_CSV,
        config.PDF_EXTRACTION_DEBUG_CSV, config.NOTICE_PARSING_DEBUG_CSV
    ]
    for log_file in log_files:
        if Path(log_file).exists():
            Path(log_file).unlink()

    # 1. Parse Notices
    notices_df = notice_parser.process_notices()
    if not notices_df.empty:
        # Save debug
        sample_size = min(100, len(notices_df))
        debug_notices = notices_df.sample(sample_size)
        debug_notices[['notice_title', 'company_name', 'notice_type', 'notice_date']].rename(columns={
            'notice_title': 'original_title',
            'company_name': 'company_detected',
            'notice_type': 'stage_detected',
            'notice_date': 'date_detected'
        }).to_csv(config.NOTICE_PARSING_DEBUG_CSV, index=False)
        
        # Clean
        notices_df = cleaner.clean_dataframe(notices_df)
        
        notices_df, stats["Duplicate Notices"] = validator.validate_notices(notices_df)
        stats["Total Notices"] = len(notices_df)
        
        # Normalize
        notices_df, unknown_notices = normalizer.normalize_dataframe(notices_df, source="notices")
        stats["Unknown Companies"] += unknown_notices
        
        notices_df.to_csv(config.NOTICES_CSV, index=False)
        logger.info(f"Saved notices.csv ({len(notices_df)} rows)")

    # 2. Parse Placement Reports
    placements_df, pdf_failures = pdf_parser.process_pdfs()
    if not placements_df.empty:
        # Save debug
        sample_size = min(100, len(placements_df))
        debug_placements = placements_df.sample(sample_size)
        debug_cols = [c for c in ['academic_year', '_page_num', 'company_name', 'placement_mode', 'ctc'] if c in debug_placements.columns]
        debug_placements[debug_cols].to_csv(config.PDF_EXTRACTION_DEBUG_CSV, index=False)
        
        if '_page_num' in placements_df.columns:
            placements_df.drop(columns=['_page_num'], inplace=True)
            
        # Clean
        placements_df = cleaner.clean_dataframe(placements_df)
        
        placements_df, stats["Invalid Placement Rows"], stats["Duplicate Student Records"] = validator.validate_placements(placements_df)
        stats["Total Placement Records"] = len(placements_df)
        
        # Normalize
        placements_df, unknown_placements = normalizer.normalize_dataframe(placements_df, source="placements")
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
        
    # Finalize Validation
    finish_time = time.time()
    duration = finish_time - start_time
    
    unique_companies = set()
    if not notices_df.empty:
        unique_companies.update(notices_df['company_name'].dropna())
    if not placements_df.empty:
        unique_companies.update(placements_df['company_name'].dropna())
        
    stats["Unique Companies"] = len(unique_companies)
    stats["Unique Students"] = stats["Total Students Processed"] - stats["Duplicate Student Records"]
    
    total_parsed = stats["Total Notices"] + stats["Total Placement Records"]
    stats["Unknown %"] = f"{(stats['Unknown Companies'] / total_parsed * 100):.2f}%" if total_parsed > 0 else "0%"
    
    stats["Execution Time"] = f"{duration:.2f} seconds"
    stats["PDF Parse Failures"] = pdf_failures
    
    with open(config.PIPELINE_METRICS_JSON, 'w') as f:
        json.dump(stats, f, indent=4)
        
    validator.generate_quality_report(stats)
    logger.info(f"Pipeline Execution Finished in {duration:.2f} seconds.")

if __name__ == "__main__":
    run()
