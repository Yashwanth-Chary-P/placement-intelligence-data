"""
run_pdf_parser.py
Orchestrates Phase 2 Placements PDF parsing, aggregation, reporting, and QA.
"""
import pandas as pd
import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts import config
from scripts.extractors import pdf_parser

REPORTS_DIR = config.PROCESSED_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def aggregate_companies(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
        
    def get_max_package(x):
        valid = [p for p in x if pd.notnull(p)]
        return max(valid) if valid else None
        
    def get_package_note(x):
        valid = [p for p in x if pd.notnull(p)]
        if len(set(valid)) > 1:
            return "Multiple packages offered"
        return ""

    agg = df.groupby(['academic_year', 'company_match_key']).agg(
        company_name=('company_name', 'first'),
        package_lpa=('package_lpa', get_max_package),
        students_placed=('placement_id', 'count'),
        package_note=('package_lpa', get_package_note)
    ).reset_index()
    
    # Reorder columns
    agg = agg[['company_name', 'company_match_key', 'academic_year', 'package_lpa', 'students_placed', 'package_note']]
    return agg

def main():
    start_time = time.time()
    print("Starting Phase 2: Placement Report PDF Parser")
    
    all_success_rows = []
    all_skipped_rows = []
    total_pdfs = 0
    total_pages = 0
    
    pdf_files = list(config.PDF_REPORTS_DIR.glob("*.pdf")) if config.PDF_REPORTS_DIR.exists() else []
    
    for pdf_file in pdf_files:
        total_pdfs += 1
        print(f"Processing {pdf_file.name}...")
        s_rows, sk_rows, pages = pdf_parser.parse_pdf(pdf_file)
        all_success_rows.extend(s_rows)
        all_skipped_rows.extend(sk_rows)
        total_pages += pages
        
    df_placements = pd.DataFrame(all_success_rows)
    df_skipped = pd.DataFrame(all_skipped_rows)
    
    # Save placements
    if not df_placements.empty:
        # Reorder to schema
        cols = ['placement_id', 'academic_year', 'roll_number', 'student_name', 
                'company_name', 'company_match_key', 'package_lpa', 'placement_mode', 
                'source_pdf', 'page_number', 'parsing_confidence']
        df_placements = df_placements[[c for c in cols if c in df_placements.columns]]
        df_placements.to_csv(config.PLACEMENTS_CSV, index=False)
        
    # Save extraction debug
    if not df_skipped.empty:
        df_skipped.to_csv(REPORTS_DIR / "extraction_debug.csv", index=False)
        
    # Aggregate Company Packages
    df_companies = aggregate_companies(df_placements)
    if not df_companies.empty:
        df_companies.to_csv(config.CSV_OUT_DIR / "company_packages.csv", index=False)
        
    # Validations & Integrity
    out_rows = len(df_placements)
    unique_companies = df_companies['company_match_key'].nunique() if not df_companies.empty else 0
    academic_years = df_companies['academic_year'].nunique() if not df_companies.empty else 0
    
    # For Phase 2, if any skipped row has "Failure reason" == "Missing company name", it's a failed placement row.
    # Header/summary skips are expected structure.
    if not df_skipped.empty:
        failed_placement_rows = df_skipped[~df_skipped['Failure reason'].str.contains('header|summary|No tables', case=False, na=False)]
    else:
        failed_placement_rows = []
    
    # Input placement rows = Output + any genuinely failed placement rows (not headers)
    input_placement_rows = out_rows + len(failed_placement_rows)
    difference = input_placement_rows - out_rows
    
    integrity_pass = (difference == 0 and len(pdf_files) > 0)
    
    # Package Statistics
    if not df_placements.empty:
        valid_packages = df_placements['package_lpa'].dropna()
        pkg_stats = {
            "Highest Package": valid_packages.max() if not valid_packages.empty else 0,
            "Lowest Package": valid_packages.min() if not valid_packages.empty else 0,
            "Average Package": valid_packages.mean() if not valid_packages.empty else 0,
            "Median Package": valid_packages.median() if not valid_packages.empty else 0,
        }
        pd.DataFrame([pkg_stats]).to_csv(REPORTS_DIR / "package_statistics.csv", index=False)
        
    # Validation samples
    if not df_placements.empty:
        sample_n = min(100, len(df_placements))
        sample_df = df_placements.sample(n=sample_n, random_state=42)
        sample_df.to_csv(REPORTS_DIR / "validation_samples_100.csv", index=False)
        
    # Company Statistics
    if not df_companies.empty:
        df_companies.to_csv(REPORTS_DIR / "company_statistics.csv", index=False)
        
    # Validation Report
    validations = {
        "Required columns present": "PASS" if not df_placements.empty else "FAIL",
        "Missing company names": "PASS" if df_placements['company_name'].isna().sum() == 0 else "FAIL",
        "Empty academic year": "PASS" if df_placements['academic_year'].isna().sum() == 0 else "FAIL",
    }
    
    with open(REPORTS_DIR / "validation_report.txt", "w", encoding='utf-8') as f:
        f.write("=== Final Validation Report ===\n")
        for k, v in validations.items():
            f.write(f"✓ {k}: {v}\n")
            
        f.write("\n==========================================\n")
        f.write("DATA INTEGRITY SUMMARY\n")
        f.write("==========================================\n")
        f.write(f"Input PDFs               : {total_pdfs}\n")
        f.write(f"Input Pages              : {total_pages}\n")
        f.write(f"Input Placement Rows     : {input_placement_rows}\n\n")
        f.write(f"Output Placement Rows    : {out_rows}\n")
        f.write(f"Difference               : {difference}\n\n")
        f.write(f"Unique Companies         : {unique_companies}\n")
        f.write(f"Academic Years           : {academic_years}\n\n")
        f.write(f"Integrity Status         : {'PASS' if integrity_pass else 'FAIL'}\n")
        f.write("==========================================\n")
        
    # Processing Report
    elapsed = time.time() - start_time
    with open(REPORTS_DIR / "processing_report.txt", "w", encoding='utf-8') as f:
        f.write(f"PDFs processed: {total_pdfs}\n")
        f.write(f"Pages processed: {total_pages}\n")
        f.write(f"Student rows extracted: {out_rows}\n")
        f.write(f"Companies extracted: {unique_companies}\n")
        f.write(f"Rows skipped: {len(df_skipped)}\n")
        f.write(f"Execution time: {elapsed:.2f}s\n")
        
    # Console Summary
    print("\n" + "="*36)
    print("Placement Report Parser Summary")
    print("="*36)
    print(f"PDFs Processed       : {total_pdfs}")
    print(f"Pages Processed      : {total_pages}")
    print(f"Students Extracted   : {out_rows}")
    print(f"Unique Companies     : {unique_companies}")
    print(f"Highest Package      : {pkg_stats['Highest Package'] if not df_placements.empty else 0}")
    avg_pkg = pkg_stats['Average Package'] if not df_placements.empty else 0
    print(f"Average Package      : {avg_pkg:.2f}")
    print(f"Rows Skipped         : {len(df_skipped)}")
    print(f"Execution Time       : {elapsed:.2f}s")
    print(f"QA Status            : {'PASS' if integrity_pass else 'FAIL'}")
    print("="*36)
    
if __name__ == "__main__":
    main()
