"""
stats_generator.py
Generates the company statistics dataset.
"""
import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("stats_generator")

def generate_company_statistics(notices_df: pd.DataFrame, placements_df: pd.DataFrame) -> pd.DataFrame:
    """Generates company_statistics.csv."""
    logger.info("Generating company statistics...")
    
    if placements_df.empty:
        logger.warning("Placements dataframe is empty.")
        return pd.DataFrame()
        
    # Aggregate placements per company
    placements_agg = placements_df.groupby('company_name').agg(
        highest_package=('ctc_lpa', 'max'),
        lowest_package=('ctc_lpa', 'min'),
        average_package=('ctc_lpa', 'mean'),
        median_package=('ctc_lpa', 'median'),
        total_students=('roll_no', 'count'),
        total_branches=('branch', lambda x: len(set(x.dropna()))),
        years_present=('academic_year', lambda x: len(set(x.dropna())))
    ).reset_index()
    
    # Notice data for visits (first visit year, month, etc)
    if not notices_df.empty:
        # Convert notice_date to datetime if not already
        notices_df['notice_date_dt'] = pd.to_datetime(notices_df['notice_date'], errors='coerce')
        
        notices_agg = notices_df.groupby('company_name').agg(
            first_visit_year=('year', 'min'),
            latest_visit_year=('year', 'max'),
            visit_count=('notice_id', 'count'),
            # Need to get month of the first visit year, but for simplicity, we get min/max of month directly
            # A more accurate way: sort by date, then group
        ).reset_index()
        
        # To get the exact first/latest month, sort and group
        sorted_notices = notices_df.dropna(subset=['notice_date_dt']).sort_values('notice_date_dt')
        if not sorted_notices.empty:
            first_months = sorted_notices.groupby('company_name')['month'].first().reset_index(name='first_visit_month')
            latest_months = sorted_notices.groupby('company_name')['month'].last().reset_index(name='latest_visit_month')
            
            notices_agg = pd.merge(notices_agg, first_months, on='company_name', how='left')
            notices_agg = pd.merge(notices_agg, latest_months, on='company_name', how='left')
        else:
            notices_agg['first_visit_month'] = None
            notices_agg['latest_visit_month'] = None
            
        stats_df = pd.merge(placements_agg, notices_agg, on='company_name', how='left')
    else:
        stats_df = placements_agg.copy()
        for col in ['first_visit_year', 'latest_visit_year', 'visit_count', 'first_visit_month', 'latest_visit_month']:
            stats_df[col] = None
            
    # Round metrics
    for col in ['highest_package', 'lowest_package', 'average_package', 'median_package']:
        stats_df[col] = stats_df[col].round(2)
        
    expected_cols = [
        'company_name', 'first_visit_year', 'latest_visit_year', 'visit_count',
        'first_visit_month', 'latest_visit_month', 'highest_package', 'lowest_package',
        'average_package', 'median_package', 'total_students', 'total_branches', 'years_present'
    ]
    
    # Ensure all expected columns exist
    for col in expected_cols:
        if col not in stats_df.columns:
            stats_df[col] = None
            
    stats_df = stats_df[expected_cols]
    
    logger.info(f"Generated company statistics with {len(stats_df)} records.")
    return stats_df
