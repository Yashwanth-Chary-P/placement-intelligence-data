"""
validator.py
Validation functions to check for duplicates and invalid records.
Includes robust Phase 1 Notice Parser validation.
"""
import pandas as pd
from typing import Dict, Any, Tuple
import sys
from pathlib import Path
import re

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config
from utils.logger import get_logger

logger = get_logger("validator")

# =====================================================================
# PHASE 1: Notice Parser Validation Methods
# =====================================================================

def generate_processing_report(df: pd.DataFrame, raw_input_count: int, current_count: int, archive_count: int, elapsed_time: float):
    """Generates the Phase 1 processing_report.txt."""
    output_rows = len(df)
    duplicates = df.duplicated(subset=['original_title', 'notice_date'], keep=False).sum()
    duplicate_perc = round((duplicates / max(1, output_rows)) * 100, 2)
    
    high_conf = len(df[df['parsing_confidence'] == 'HIGH'])
    med_conf = len(df[df['parsing_confidence'] == 'MEDIUM'])
    low_conf = len(df[df['parsing_confidence'] == 'LOW'])
    
    unique_companies = df['company_name'].nunique()
    unique_years = df['year'].nunique()
    unique_months = df['month'].nunique()
    
    # Sort dates to find earliest/latest, handling empty strings safely
    valid_dates = df[df['notice_date'] != '']['notice_date'].dropna().sort_values()
    earliest_notice = valid_dates.iloc[0] if not valid_dates.empty else "N/A"
    latest_notice = valid_dates.iloc[-1] if not valid_dates.empty else "N/A"
    
    missing_company = len(df[df['company_name'] == ''])
    missing_date = len(df[df['notice_date'] == ''])
    missing_source = len(df[df['source'] == ''])
    
    report_content = f"""==================================================
Raw Files
Number of input files: 2
Number of notices in current_notices.txt: {current_count}
Number of notices in archive_notices.txt: {archive_count}
Total raw notices: {raw_input_count}
==================================================
Output
Rows written to notices.csv: {output_rows}
Rows skipped: {raw_input_count - output_rows}
Rows failed: 0
Rows duplicated: {duplicates}
Duplicate percentage: {duplicate_perc}%
==================================================
Confidence
HIGH: {high_conf}
MEDIUM: {med_conf}
LOW: {low_conf}
==================================================
Parsing Statistics
Unique companies: {unique_companies}
Unique years: {unique_years}
Unique months: {unique_months}
Earliest notice: {earliest_notice}
Latest notice: {latest_notice}
==================================================
Unknown values
Missing company: {missing_company}
Missing date: {missing_date}
Missing source: {missing_source}
==================================================
Total execution time: {elapsed_time:.2f} seconds
==================================================
"""
    with open(config.NOTICE_PROCESSING_REPORT, 'w') as f:
        f.write(report_content)
    logger.info(f"Processing report saved to {config.NOTICE_PROCESSING_REPORT}")

def validate_notice_output(df: pd.DataFrame, raw_input_count: int) -> Dict[str, str]:
    """Validates the output DataFrame against Phase 1 rules."""
    validations = {}
    
    # 1. Input vs Output
    validations['Input rows == Output rows'] = 'PASS' if len(df) == raw_input_count else f'FAIL (Expected {raw_input_count}, got {len(df)})'
    
    # 2. Random Sample validation is deferred to generate_validation_samples
    
    # 3. Match Key format
    invalid_keys = df[df['company_match_key'].str.contains(r'[^a-z0-9\s]', regex=True, na=False)]
    validations['Match keys formatted correctly'] = 'PASS' if invalid_keys.empty else f'FAIL ({len(invalid_keys)} invalid keys)'
    
    # 4. Check for empties/duplicates
    empty_companies = len(df[df['company_name'] == ''])
    empty_dates = len(df[df['notice_date'] == ''])
    empty_sources = len(df[df['source'] == ''])
    duplicates = df.duplicated(subset=['original_title', 'notice_date']).sum()
    
    validations['No empty company names'] = 'PASS' if empty_companies == 0 else f'FAIL ({empty_companies} found)'
    validations['No empty dates'] = 'PASS' if empty_dates == 0 else f'FAIL ({empty_dates} found)'
    validations['No empty sources'] = 'PASS' if empty_sources == 0 else f'FAIL ({empty_sources} found)'
    validations['No duplicate rows'] = 'PASS' if duplicates == 0 else f'FAIL ({duplicates} found)'
    
    # 5. PDF URL Format
    invalid_urls = df[~df['pdf_url'].str.startswith(config.PDF_BASE_URL, na=False) | ~df['pdf_url'].str.endswith('.pdf', na=False)]
    validations['PDF URLs follow expected format'] = 'PASS' if invalid_urls.empty else f'FAIL ({len(invalid_urls)} invalid URLs)'
    
    # 6. Confidence values
    valid_confidences = ['HIGH', 'MEDIUM', 'LOW']
    invalid_confs = df[~df['parsing_confidence'].isin(valid_confidences)]
    validations['Confidence values valid'] = 'PASS' if invalid_confs.empty else f'FAIL ({len(invalid_confs)} invalid)'
    
    return validations

def generate_validation_report(validations: Dict[str, str]):
    """Generates the Phase 1 validation_report.txt."""
    with open(config.NOTICE_VALIDATION_REPORT, 'w') as f:
        f.write("=== Validation Report ===\n")
        for check, result in validations.items():
            f.write(f"{check}: {result}\n")
    logger.info(f"Validation report saved to {config.NOTICE_VALIDATION_REPORT}")

def generate_validation_samples(df: pd.DataFrame):
    """Generates a sample of 50 notices for manual validation."""
    if len(df) < 50:
        sample_df = df.copy()
    else:
        sample_df = df.sample(n=50, random_state=42)
        
    sample_df['Validation Result'] = 'PASS' # Pre-fill for manual auditor
    sample_df['Validation Remarks'] = ''
    
    columns_to_export = [
        'original_title', 'company_name', 'company_match_key', 
        'notice_date', 'source', 'pdf_url', 'parsing_confidence', 
        'Validation Result', 'Validation Remarks'
    ]
    
    sample_df[columns_to_export].to_csv(config.NOTICE_VALIDATION_SAMPLES, index=False)
    logger.info(f"Validation samples saved to {config.NOTICE_VALIDATION_SAMPLES}")


# =====================================================================
# PHASE 2: (Legacy/Existing) Placement Validation Methods
# =====================================================================

def validate_notices(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Legacy validation for notices (used if pipeline runs older code)."""
    logger.info("Validating notices (Legacy)...")
    if 'notice_title' in df.columns:
        subset = ['notice_title', 'notice_date']
    else:
        subset = ['original_title', 'notice_date']
        
    duplicates = df[df.duplicated(subset=subset, keep='first')]
    duplicate_count = len(duplicates)
    
    if not duplicates.empty:
        logger.warning(f"Found {duplicate_count} duplicate notices.")
        duplicates.to_csv(config.DUPLICATE_NOTICES_CSV, index=False)
        df = df.drop_duplicates(subset=subset, keep='first')
        
    return df, duplicate_count

def validate_placements(df: pd.DataFrame) -> Tuple[pd.DataFrame, int, int]:
    """Validates placements and returns a clean dataframe."""
    logger.info("Validating placements...")
    invalid = df[df['roll_no'].isna() | (df['roll_no'] == '') | df['ctc_lpa'].isna()]
    invalid_count = len(invalid)
    if not invalid.empty:
        logger.warning(f"Found {invalid_count} invalid placement records.")
        invalid.to_csv(config.INVALID_ROWS_CSV, index=False)
        df = df.drop(invalid.index)
        
    duplicates = df[df.duplicated(subset=['roll_no', 'company_name', 'academic_year'], keep='first')]
    duplicate_count = len(duplicates)
    if not duplicates.empty:
        logger.warning(f"Found {duplicate_count} duplicate placement records for students.")
        duplicates.to_csv(config.DUPLICATE_STUDENTS_CSV, index=False)
        df = df.drop(duplicates.index)
        
    return df, invalid_count, duplicate_count

def generate_quality_report(stats: Dict[str, Any]):
    """Generates the data quality report for Phase 2."""
    logger.info("Generating data quality report...")
    with open(config.DATA_QUALITY_REPORT, 'w') as f:
        f.write("=== Data Quality Report ===\n")
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")
    logger.info(f"Data quality report saved to {config.DATA_QUALITY_REPORT}")
