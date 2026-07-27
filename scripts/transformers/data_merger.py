"""
data_merger.py
Merges notices and placements into a master dataset.
"""
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("data_merger")

def generate_master_dataset(notices_df: pd.DataFrame, placements_df: pd.DataFrame) -> pd.DataFrame:
    """Merges notices and placements into company_placement_master.csv."""
    logger.info("Generating master dataset...")
    
    if placements_df.empty:
        logger.warning("Placements dataframe is empty.")
        return pd.DataFrame()
        
    # Aggregate placements by company and academic_year
    placements_agg = placements_df.groupby(['company_name', 'academic_year']).agg(
        students_selected=('roll_no', 'count'),
        highest_ctc=('ctc_lpa', 'max'),
        average_ctc=('ctc_lpa', 'mean'),
        minimum_ctc=('ctc_lpa', 'min'),
        placement_modes=('placement_mode', lambda x: ', '.join(sorted(set(x.dropna())))),
        branches_hired=('branch', lambda x: ', '.join(sorted(set(x.dropna()))))
    ).reset_index()
    
    # Notice dates might cross academic years. We need to join notices to placements.
    # Since notices don't have academic_year explicitly (they have year/month/date), 
    # we can try to map them, but it's simpler to aggregate notices by company first,
    # or just join on company_name and pick the most relevant notice for that academic year.
    # For now, let's aggregate notices per company to get first_notice, last_notice, pdf_urls, etc.
    if not notices_df.empty:
        notices_agg = notices_df.groupby('company_name').agg(
            first_notice_date=('notice_date', 'min'),
            last_notice_date=('notice_date', 'max'),
            notice_type=('notice_type', lambda x: ', '.join(sorted(set([str(i) for i in x if str(i).strip()])))),
            pdf_url=('pdf_url', 'first'),  # Or join all URLs
            notice_date=('notice_date', 'first'),
            year=('year', 'first'),
            month=('month', 'first')
        ).reset_index()
        
        # Merge placement aggregates with notice aggregates
        master_df = pd.merge(placements_agg, notices_agg, on='company_name', how='left')
    else:
        master_df = placements_agg.copy()
        for col in ['first_notice_date', 'last_notice_date', 'notice_type', 'pdf_url', 'notice_date', 'year', 'month']:
            master_df[col] = None
            
    # Round CTC values
    for col in ['highest_ctc', 'average_ctc', 'minimum_ctc']:
        master_df[col] = master_df[col].round(2)
        
    expected_cols = [
        'company_name', 'academic_year', 'notice_date', 'year', 'month',
        'notice_type', 'pdf_url', 'students_selected', 'highest_ctc', 
        'average_ctc', 'minimum_ctc', 'placement_modes', 'branches_hired',
        'first_notice_date', 'last_notice_date'
    ]
    
    # Ensure all expected columns exist
    for col in expected_cols:
        if col not in master_df.columns:
            master_df[col] = None
            
    master_df = master_df[expected_cols]
    
    logger.info(f"Generated master dataset with {len(master_df)} records.")
    return master_df
