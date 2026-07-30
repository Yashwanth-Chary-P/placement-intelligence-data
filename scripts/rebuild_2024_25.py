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
    if not isinstance(a, str) or not isinstance(b, str):
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def main():
    print("Starting 2024-25 Focused Rebuild")
    
    # 1. Load Data
    notices_df = pd.read_csv(config.NOTICES_CSV)
    placements_df = pd.read_csv(config.PLACEMENTS_CSV)
    
    # 2. Filter to 2024-25
    notices_df['academic_year'] = notices_df['notice_date'].apply(
        lambda x: derive_academic_year(x, config.ACADEMIC_YEAR_START_MONTH)
    )
    notices_2425 = notices_df[notices_df['academic_year'] == '2024-25'].copy()
    placements_2425 = placements_df[placements_df['academic_year'] == '2024-25'].copy()
    
    print(f"Notices for 2024-25: {len(notices_2425)}")
    print(f"Placement records for 2024-25: {len(placements_2425)}")
    
    # 3. Aggregate Placements Data
    placement_agg = placements_2425.groupby('company_match_key').agg(
        placement_company_name=('company_name', 'first'),
        package_lpa=('package_lpa', 'max'),
        students_placed=('roll_number', 'nunique')
    ).reset_index()
    
    # 4. Create Company Mapping
    unique_notices = notices_2425[['company_name', 'company_match_key']].drop_duplicates()
    unique_notices.rename(columns={'company_name': 'notice_company_name'}, inplace=True)
    
    mapping_df = pd.merge(unique_notices, placement_agg[['company_match_key', 'placement_company_name']], 
                          on='company_match_key', how='left')
    
    def determine_status(row):
        if pd.isna(row['placement_company_name']):
            return "Unmatched"
        if row['notice_company_name'].strip().lower() == row['placement_company_name'].strip().lower():
            return "Exact Match"
        return "Alias Match"
    
    mapping_df['mapping_status'] = mapping_df.apply(determine_status, axis=1)
    
    mapping_out_path = config.CSV_OUT_DIR / "company_mapping_2024_25.csv"
    mapping_df.to_csv(mapping_out_path, index=False)
    print(f"Saved company mapping to {mapping_out_path}")
    
    # 5. Golden Dataset Generation
    # Preserve every notice, left join with aggregated placement data
    intel_df = pd.merge(notices_2425, placement_agg, on='company_match_key', how='left')
    
    intel_cols = ['company_name', 'company_match_key', 'notice_date', 'month', 'academic_year', 
                  'original_title', 'pdf_url', 'package_lpa', 'students_placed']
    intel_df_out = intel_df[intel_cols]
    
    intel_out_path = config.CSV_OUT_DIR / "company_intelligence_2024_25.csv"
    intel_df_out.to_csv(intel_out_path, index=False)
    print(f"Saved golden dataset to {intel_out_path} ({len(intel_df_out)} rows)")
    
    # 6. Manual Validation Report (Unmatched companies)
    unmatched_df = mapping_df[mapping_df['mapping_status'] == 'Unmatched'].copy()
    
    placement_companies = placement_agg['placement_company_name'].dropna().unique().tolist()
    
    review_rows = []
    for _, row in unmatched_df.iterrows():
        notice_comp = row['notice_company_name']
        best_match = None
        best_score = 0.0
        for p_comp in placement_companies:
            score = similarity(notice_comp, p_comp)
            if score > best_score:
                best_score = score
                best_match = p_comp
        
        review_rows.append({
            'Notice Company': notice_comp,
            'Closest Placement Company': best_match,
            'Suggested Match': best_match,
            'Confidence': round(best_score * 100, 2),
            'Recommendation': 'Likely Match' if best_score > 0.8 else 'Review'
        })
    
    review_df = pd.DataFrame(review_rows)
    review_out_path = config.REPORTS_DIR / "company_mapping_review.csv"
    review_df.to_csv(review_out_path, index=False)
    print(f"Saved mapping review report to {review_out_path}")
    
    # 7. Top Company Validation
    major_recruiters = [
        "Microsoft", "Amazon", "Google", "Oracle", "Salesforce", "ServiceNow", 
        "JPMorgan Chase", "Qualcomm", "Adobe", "Deloitte", "Accenture", 
        "Infosys", "TCS", "Cognizant", "Capgemini", "UBS", "Tata Consultancy Services"
    ]
    major_keys = [k.lower().replace(" ", "") for k in major_recruiters]
    
    # Let's find them using substring match on company_match_key
    top_rows = []
    for _, row in mapping_df.iterrows():
        key = row['company_match_key']
        is_major = False
        for m in major_keys:
            if m in str(key):
                is_major = True
                break
        if not is_major:
            # check notice_company_name as well
            name_lower = row['notice_company_name'].lower()
            for m in major_recruiters:
                if m.lower() in name_lower:
                    is_major = True
                    break
                    
        if is_major:
            n_data = intel_df[intel_df['company_match_key'] == key]
            if len(n_data) > 0:
                top_rows.append({
                    'Company Name': row['notice_company_name'],
                    'Number of Notices': len(n_data),
                    'Notice Dates': ", ".join(n_data['notice_date'].dropna().astype(str).tolist()),
                    'Package (LPA)': n_data['package_lpa'].iloc[0] if pd.notnull(n_data['package_lpa'].iloc[0]) else "N/A",
                    'Students Placed': n_data['students_placed'].iloc[0] if pd.notnull(n_data['students_placed'].iloc[0]) else 0,
                    'Mapping Status': row['mapping_status']
                })
    
    top_df = pd.DataFrame(top_rows)
    # Deduplicate in case multiple notice names matched same major recruiter
    if not top_df.empty:
        top_df = top_df.drop_duplicates(subset=['Company Name'])
        
    top_out_path = config.REPORTS_DIR / "top_companies_validation.csv"
    top_df.to_csv(top_out_path, index=False)
    print(f"Saved top companies validation report to {top_out_path}")
    
    # 8. Validation Output
    total_companies = len(mapping_df)
    matched_companies = len(mapping_df[mapping_df['mapping_status'] != 'Unmatched'])
    unmatched_companies = len(mapping_df[mapping_df['mapping_status'] == 'Unmatched'])
    mapping_percentage = (matched_companies / total_companies * 100) if total_companies > 0 else 0
    
    notices_preserved = len(intel_df_out) == len(notices_2425)
    
    report_lines = [
        "=== 2024-25 Golden Dataset Validation Report ===",
        f"Total 2024-25 Notices Processed: {len(notices_2425)}",
        f"Total 2024-25 Placements Processed: {len(placements_2425)}",
        f"Output Notices in Golden Dataset: {len(intel_df_out)}",
        f"Notices Preserved: {'PASS' if notices_preserved else 'FAIL'}",
        "",
        "--- Mapping Summary ---",
        f"Total Notice Companies: {total_companies}",
        f"Matched Companies: {matched_companies}",
        f"Unmatched Companies: {unmatched_companies}",
        f"Mapping Percentage: {mapping_percentage:.2f}%",
        "",
        "--- Mapping Breakdown ---",
        f"Exact Matches: {len(mapping_df[mapping_df['mapping_status'] == 'Exact Match'])}",
        f"Alias Matches: {len(mapping_df[mapping_df['mapping_status'] == 'Alias Match'])}",
        "",
        "Validation complete."
    ]
    
    val_out_path = config.REPORTS_DIR / "validation_report_2024_25.txt"
    with open(val_out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Saved validation report to {val_out_path}")
    
if __name__ == "__main__":
    main()
