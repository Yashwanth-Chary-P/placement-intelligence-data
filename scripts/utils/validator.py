"""
validator.py
Validation functions to check for duplicates and invalid records.
"""
import pandas as pd
from typing import Dict, Any, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from utils.logger import get_logger

logger = get_logger("validator")

def validate_notices(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Validates notices and returns a clean dataframe and duplicate count."""
    logger.info("Validating notices...")
    
    duplicates = df[df.duplicated(subset=['notice_title', 'notice_date'], keep='first')]
    duplicate_count = len(duplicates)
    
    if not duplicates.empty:
        logger.warning(f"Found {duplicate_count} duplicate notices.")
        duplicates.to_csv(config.DUPLICATE_NOTICES_CSV, index=False)
        df = df.drop_duplicates(subset=['notice_title', 'notice_date'], keep='first')
        
    return df, duplicate_count

def validate_placements(df: pd.DataFrame) -> Tuple[pd.DataFrame, int, int]:
    """Validates placements and returns a clean dataframe, invalid count, and duplicate count."""
    logger.info("Validating placements...")
    
    # Invalid rows (missing roll_no or ctc)
    invalid = df[df['roll_no'].isna() | (df['roll_no'] == '') | df['ctc_lpa'].isna()]
    invalid_count = len(invalid)
    if not invalid.empty:
        logger.warning(f"Found {invalid_count} invalid placement records.")
        # Append mode just in case, but usually overwriting is fine for pipeline run
        invalid.to_csv(config.INVALID_ROWS_CSV, index=False)
        df = df.drop(invalid.index)
        
    # Check for duplicate students in the same company/year
    duplicates = df[df.duplicated(subset=['roll_no', 'company_name', 'academic_year'], keep='first')]
    duplicate_count = len(duplicates)
    if not duplicates.empty:
        logger.warning(f"Found {duplicate_count} duplicate placement records for students.")
        duplicates.to_csv(config.DUPLICATE_STUDENTS_CSV, index=False)
        df = df.drop(duplicates.index)
        
    return df, invalid_count, duplicate_count

def generate_quality_report(stats: Dict[str, Any]):
    """Generates the data quality report."""
    logger.info("Generating data quality report...")
    with open(config.DATA_QUALITY_REPORT, 'w') as f:
        f.write("=== Data Quality Report ===\n")
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")
    logger.info(f"Data quality report saved to {config.DATA_QUALITY_REPORT}")
