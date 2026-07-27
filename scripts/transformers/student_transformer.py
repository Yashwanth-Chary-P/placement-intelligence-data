"""
student_transformer.py
Generates the students dataset with LinkedIn search URLs.
"""
import pandas as pd
import urllib.parse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("student_transformer")

def generate_students_dataset(placements_df: pd.DataFrame) -> pd.DataFrame:
    """Generates the students dataset by enriching placement data."""
    logger.info("Generating students dataset...")
    
    if placements_df.empty:
        logger.warning("Placements dataframe is empty.")
        return pd.DataFrame()
        
    # Copy to avoid modifying the original dataframe
    students_df = placements_df.copy()
    
    # Generate LinkedIn search URL
    students_df['linkedin_search_url'] = students_df['student_name'].apply(
        lambda name: config.LINKEDIN_SEARCH_BASE + urllib.parse.quote(str(name))
    )
    
    # Ensure columns match requirements
    expected_cols = [
        'roll_no', 'student_name', 'branch', 'company_name', 
        'academic_year', 'placement_mode', 'ctc_lpa', 'linkedin_search_url'
    ]
    
    # Filter only expected columns that exist
    final_cols = [col for col in expected_cols if col in students_df.columns]
    students_df = students_df[final_cols]
    
    logger.info(f"Generated students dataset with {len(students_df)} records.")
    return students_df
