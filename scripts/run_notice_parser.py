"""
run_notice_parser.py
Dedicated runner for Phase 1: Notice Parser.
"""
import sys
from pathlib import Path
import time
import logging

sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts import config
from scripts.extractors import notice_parser
from scripts.utils import validator

# Reconfigure logger specifically for this phase
logger = logging.getLogger("notice_parser_runner")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(config.NOTICE_PARSER_LOG, mode='w')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def count_raw_notices(file_path: Path) -> int:
    if not file_path.exists():
        return 0
    with open(file_path, 'r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())

def main():
    start_time = time.time()
    logger.info("Starting Phase 1: Notice Parser")
    
    # 1. Count Raw Inputs
    current_count = count_raw_notices(config.NOTICES_CURRENT_DIR / "current_notices.txt") if config.NOTICES_CURRENT_DIR.exists() else 0
    
    # It seems in the instructions the files were current_notices.txt, archive_notices.txt
    # Let's count them exactly.
    curr_file = config.NOTICES_CURRENT_DIR / "current_notices.txt"
    arch_file = config.NOTICES_ARCHIVE_DIR / "archive_notices.txt"
    
    current_count = count_raw_notices(curr_file)
    archive_count = count_raw_notices(arch_file)
    total_raw = current_count + archive_count
    
    logger.info(f"Discovered {total_raw} raw notices across {2 if current_count and archive_count else 1} files.")
    
    # 2. Execute Parser
    df = notice_parser.process_notices()
    
    output_rows = len(df)
    
    # 3. Validation
    logger.info("Validating parsed data...")
    validations = validator.validate_notice_output(df, total_raw)
    validator.generate_validation_report(validations)
    validator.generate_validation_samples(df)
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # 4. Processing Report
    validator.generate_processing_report(df, total_raw, current_count, archive_count, elapsed)
    
    # 5. Save Final Output
    df.to_csv(config.NOTICES_CSV, index=False)
    logger.info(f"Saved strictly formatted notices to {config.NOTICES_CSV}")
    
    # 6. Console Summary
    logger.info("\n" + "="*50)
    logger.info("Phase 1 Execution Summary")
    logger.info("="*50)
    logger.info(f"Raw notices: {total_raw}")
    logger.info(f"Output rows: {output_rows}")
    logger.info(f"Success %:   {round((output_rows/total_raw)*100, 2) if total_raw > 0 else 0}%")
    logger.info(f"Unique companies: {df['company_name'].nunique()}")
    
    high = len(df[df['parsing_confidence'] == 'HIGH'])
    med = len(df[df['parsing_confidence'] == 'MEDIUM'])
    low = len(df[df['parsing_confidence'] == 'LOW'])
    
    logger.info(f"High confidence:   {round((high/output_rows)*100, 2) if output_rows > 0 else 0}%")
    logger.info(f"Medium confidence: {round((med/output_rows)*100, 2) if output_rows > 0 else 0}%")
    logger.info(f"Low confidence:    {round((low/output_rows)*100, 2) if output_rows > 0 else 0}%")
    logger.info("="*50)

if __name__ == "__main__":
    main()
