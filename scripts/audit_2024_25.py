import pandas as pd
import sys
from pathlib import Path
from difflib import SequenceMatcher

sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts import config

def derive_academic_year(date_str: str, start_month: int) -> str:
    try:
        if pd.isna(date_str) or not date_str:
            return "Unknown"
        dt = pd.to_datetime(date_str)
        if pd.isna(dt):
            return "Unknown"
        if dt.month >= start_month:
            return f"{dt.year}-{str(dt.year + 1)[-2:]}"
        else:
            return f"{dt.year - 1}-{str(dt.year)[-2:]}"
    except Exception:
        return "Unknown"

def similarity(a, b):
    if pd.isna(a) or pd.isna(b):
        return 0.0
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()

def main():
    print("Starting Company Mapping Audit 2024-25")
    
    # Load Data
    notices_df = pd.read_csv(config.NOTICES_CSV)
    placements_df = pd.read_csv(config.PLACEMENTS_CSV)
    
    # Filter 2024-25
    notices_df['academic_year'] = notices_df['notice_date'].apply(
        lambda x: derive_academic_year(x, config.ACADEMIC_YEAR_START_MONTH)
    )
    notices_2425 = notices_df[notices_df['academic_year'] == '2024-25'].copy()
    placements_2425 = placements_df[placements_df['academic_year'] == '2024-25'].copy()
    
    # Step 1: Distinct Placement Companies
    # Calculate total records, distinct companies, list of distinct names, keys
    placement_total = len(placements_2425)
    distinct_placement_keys = placements_2425['company_match_key'].nunique()
    
    dist_place_df = placements_2425.groupby('company_match_key').agg(
        placement_company_name=('company_name', 'first'),
        placement_record_count=('roll_number', 'count')
    ).reset_index()
    dist_place_df = dist_place_df.sort_values('placement_record_count', ascending=False)
    
    out_place = config.REPORTS_DIR / "distinct_placement_companies.csv"
    dist_place_df[['placement_company_name', 'company_match_key', 'placement_record_count']].to_csv(out_place, index=False)
    
    # Step 2: Distinct Notice Companies
    notice_total = len(notices_2425)
    distinct_notice_keys = notices_2425['company_match_key'].nunique()
    
    # Create list of notice dates chronologically
    def get_sorted_dates(dates):
        d_list = dates.dropna().tolist()
        d_list.sort()
        return ", ".join(d_list)
        
    dist_notices_df = notices_2425.groupby('company_match_key').agg(
        notice_company_name=('company_name', 'first'),
        notice_count=('notice_date', 'count'),
        notice_dates=('notice_date', get_sorted_dates)
    ).reset_index()
    dist_notices_df = dist_notices_df.sort_values('notice_count', ascending=False)
    
    out_notice = config.REPORTS_DIR / "distinct_notice_companies.csv"
    dist_notices_df[['notice_company_name', 'company_match_key', 'notice_count', 'notice_dates']].to_csv(out_notice, index=False)
    
    # Step 3: Mapping Audit
    audit_df = pd.merge(dist_place_df, dist_notices_df, on='company_match_key', how='outer')
    
    def get_mapping_status(row):
        has_p = pd.notna(row['placement_record_count']) and row['placement_record_count'] > 0
        has_n = pd.notna(row['notice_count']) and row['notice_count'] > 0
        
        if has_p and has_n:
            if row['notice_count'] > 1:
                return "Multiple Notices"
            else:
                return "Exact Match"
        elif has_p and not has_n:
            return "Placement Only"
        elif has_n and not has_p:
            return "Notice Only"
        return "Unmatched"
        
    audit_df['mapping_status'] = audit_df.apply(get_mapping_status, axis=1)
    
    # Reorder columns
    audit_cols = ['placement_company_name', 'notice_company_name', 'company_match_key', 
                  'placement_record_count', 'notice_count', 'notice_dates', 'mapping_status']
    
    out_audit = config.REPORTS_DIR / "company_mapping_audit.csv"
    audit_df[audit_cols].to_csv(out_audit, index=False)
    
    # Step 4: Multiple Notice Detection
    multi_notice_df = audit_df[audit_df['mapping_status'] == 'Multiple Notices'].copy()
    
    # Need notice_titles. Group notices again.
    def get_notice_titles(keys):
        # We'll just map from notices_2425
        pass

    multi_rows = []
    for _, row in multi_notice_df.iterrows():
        key = row['company_match_key']
        n_data = notices_2425[notices_2425['company_match_key'] == key].sort_values('notice_date')
        multi_rows.append({
            'company_name': row['placement_company_name'] if pd.notna(row['placement_company_name']) else row['notice_company_name'],
            'company_match_key': key,
            'number_of_notices': row['notice_count'],
            'notice_dates': ", ".join(n_data['notice_date'].dropna().astype(str).tolist()),
            'notice_titles': " | ".join(n_data['original_title'].dropna().tolist())
        })
    multi_out_df = pd.DataFrame(multi_rows).sort_values('number_of_notices', ascending=False) if multi_rows else pd.DataFrame()
    out_multi = config.REPORTS_DIR / "multiple_notice_mapping.csv"
    multi_out_df.to_csv(out_multi, index=False)
    
    # Step 5: Top Companies
    # Get stats per placement company
    top_rows = []
    for _, row in dist_place_df.iterrows():
        key = row['company_match_key']
        p_data = placements_2425[placements_2425['company_match_key'] == key]
        n_data = notices_2425[notices_2425['company_match_key'] == key].sort_values('notice_date')
        
        status = audit_df[audit_df['company_match_key'] == key]['mapping_status'].iloc[0]
        
        top_rows.append({
            'Company Name': row['placement_company_name'],
            'Placement Records': len(p_data),
            'Students Placed': p_data['roll_number'].nunique(),
            'Package': p_data['package_lpa'].max() if not p_data['package_lpa'].dropna().empty else "N/A",
            'Number of Notices': len(n_data),
            'Notice Dates': ", ".join(n_data['notice_date'].dropna().astype(str).tolist()) if not n_data.empty else "N/A",
            'Mapping Status': status
        })
        
    top_df = pd.DataFrame(top_rows)
    out_top = config.REPORTS_DIR / "top_company_mapping.csv"
    top_df.to_csv(out_top, index=False)
    
    # Step 7: Manual Review (do this before Step 6 to get stats)
    # Include companies that require manual inspection (Placement Only)
    manual_rows = []
    notice_companies = dist_notices_df['notice_company_name'].dropna().unique().tolist()
    
    unmapped_placements = audit_df[audit_df['mapping_status'] == 'Placement Only']
    for _, row in unmapped_placements.iterrows():
        p_comp = row['placement_company_name']
        best_match = None
        best_score = 0.0
        for n_comp in notice_companies:
            score = similarity(p_comp, n_comp)
            if score > best_score:
                best_score = score
                best_match = n_comp
                
        manual_rows.append({
            'Placement Company': p_comp,
            'Closest Notice Company': best_match,
            'Similarity Score': round(best_score * 100, 2),
            'Suggested Alias': best_match if best_score > 0.7 else "None",
            'Recommendation': 'Likely Match' if best_score > 0.8 else 'Review'
        })
        
    manual_df = pd.DataFrame(manual_rows).sort_values('Similarity Score', ascending=False) if manual_rows else pd.DataFrame()
    out_manual = config.REPORTS_DIR / "manual_mapping_review.csv"
    manual_df.to_csv(out_manual, index=False)
    
    # Step 6: Summary Statistics
    mapped_companies = len(audit_df[audit_df['mapping_status'].isin(['Exact Match', 'Multiple Notices'])])
    unmapped_placement_comps = len(audit_df[audit_df['mapping_status'] == 'Placement Only'])
    unmapped_notice_comps = len(audit_df[audit_df['mapping_status'] == 'Notice Only'])
    companies_with_multiple_notices = len(multi_notice_df)
    
    highest_notices = dist_notices_df['notice_count'].max() if not dist_notices_df.empty else 0
    avg_notices = dist_notices_df['notice_count'].mean() if not dist_notices_df.empty else 0
    
    summary_text = f"""==================================
COMPANY MAPPING AUDIT
==================================
Placement Records                  : {placement_total}
Distinct Placement Companies       : {distinct_placement_keys}
Notice Records                     : {notice_total}
Distinct Notice Companies          : {distinct_notice_keys}
Mapped Companies                   : {mapped_companies}
Unmapped Placement Companies       : {unmapped_placement_comps}
Unmapped Notice Companies          : {unmapped_notice_comps}
Companies With Multiple Notices    : {companies_with_multiple_notices}
Highest Number Of Notices For One Company : {highest_notices}
Average Notices Per Company        : {avg_notices:.2f}
=================================="""

    print(summary_text)
    out_summary = config.REPORTS_DIR / "company_mapping_summary.txt"
    with open(out_summary, "w", encoding="utf-8") as f:
        f.write(summary_text)
        
if __name__ == "__main__":
    main()
