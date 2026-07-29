"""
config.py
Centralized configuration for the Placement Intelligence Data Pipeline.
"""
import json
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "raw"
PROCESSED_DIR = PROJECT_ROOT / "processed"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Input Paths
NOTICES_CURRENT_DIR = RAW_DIR / "notices" / "current"
NOTICES_ARCHIVE_DIR = RAW_DIR / "notices" / "archive"
PDF_REPORTS_DIR = RAW_DIR / "placement_reports"

# Output Paths
CSV_OUT_DIR = PROCESSED_DIR / "csv"
LOGS_OUT_DIR = PROCESSED_DIR / "logs"
REPORTS_DIR = PROCESSED_DIR / "reports"

CSV_OUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Output Files
NOTICES_CSV = CSV_OUT_DIR / "notices.csv"
PLACEMENTS_CSV = CSV_OUT_DIR / "placements.csv"
COMPANY_PACKAGES_CSV = CSV_OUT_DIR / "company_packages.csv"
STUDENTS_CSV = CSV_OUT_DIR / "students.csv"
COMPANY_PLACEMENT_MASTER_CSV = CSV_OUT_DIR / "company_placement_master.csv"
COMPANY_STATISTICS_CSV = CSV_OUT_DIR / "company_statistics.csv"

# Phase 3 Output Files
COMPANY_INTELLIGENCE_CSV = CSV_OUT_DIR / "company_intelligence.csv"
COMPANY_SUMMARY_CSV = CSV_OUT_DIR / "company_summary.csv"
COMPANY_MONTHLY_INTELLIGENCE_CSV = CSV_OUT_DIR / "company_monthly_intelligence.csv"
MONTHLY_STATISTICS_CSV = CSV_OUT_DIR / "monthly_statistics.csv"
PACKAGE_DISTRIBUTION_CSV = CSV_OUT_DIR / "package_distribution.csv"
COMPANY_TIMELINE_CSV = CSV_OUT_DIR / "company_timeline.csv"

# Log Files
PIPELINE_LOG = LOGS_OUT_DIR / "pipeline.log"
DATA_QUALITY_REPORT = LOGS_OUT_DIR / "data_quality_report.txt"
UNKNOWN_COMPANIES_CSV = LOGS_OUT_DIR / "unknown_companies.csv"
DUPLICATE_STUDENTS_CSV = LOGS_OUT_DIR / "duplicate_students.csv"
DUPLICATE_NOTICES_CSV = LOGS_OUT_DIR / "duplicate_notices.csv"
INVALID_ROWS_CSV = LOGS_OUT_DIR / "invalid_rows.csv"

# New Audit/Debug Files
COMPANY_NORMALIZATION_AUDIT_CSV = LOGS_OUT_DIR / "company_normalization_audit.csv"
PDF_EXTRACTION_DEBUG_CSV = LOGS_OUT_DIR / "pdf_extraction_debug.csv"
NOTICE_PARSING_DEBUG_CSV = LOGS_OUT_DIR / "notice_parsing_debug.csv"
PIPELINE_METRICS_JSON = LOGS_OUT_DIR / "pipeline_metrics.json"

# Phase 1 Notice Parser specific files
NOTICE_PARSER_LOG = LOGS_OUT_DIR / "notice_parser.log"
NOTICE_PROCESSING_REPORT = LOGS_OUT_DIR / "processing_report.txt"
NOTICE_VALIDATION_REPORT = LOGS_OUT_DIR / "validation_report.txt"
NOTICE_VALIDATION_SAMPLES = CSV_OUT_DIR / "validation_samples.csv"

# URL Configs
PDF_BASE_URL = "https://www.cbit.ac.in/wp-content/uploads/2019/12/"
LINKEDIN_SEARCH_BASE = "https://www.linkedin.com/search/results/all/?keywords="

# Fuzzy Matching Config
FUZZY_MATCH_THRESHOLD = 85.0

# Merge Engine Config
ACADEMIC_YEAR_START_MONTH = 7

# Supported Notice Stages (Order by length descending to match longest first)
_keywords_file = PROJECT_ROOT / "config" / "notice_stage_keywords.json"
try:
    with open(_keywords_file, 'r', encoding='utf-8') as _f:
        _loaded_stages = json.load(_f)
except Exception as e:
    _loaded_stages = []

NOTICE_STAGES = sorted(_loaded_stages, key=len, reverse=True)

# Company Alias Dictionary (Exact overrides)
COMPANY_ALIASES = {
    "JP Morgan": "JP Morgan Chase",
    "JP Morgan chase": "JP Morgan Chase",
    "J.P. Morgan": "JP Morgan Chase",
    "JPMC": "JP Morgan Chase",
    "Electronic Arts": "Electronic Arts",
    "Electronics Arts": "Electronic Arts",
    "EA": "Electronic Arts",
    "ServiceNow": "ServiceNow",
    "Servicenow": "ServiceNow",
    "Service Now": "ServiceNow",
    "Infosys": "Infosys",
    "Ifosys": "Infosys",
    "Deloitte Tax": "Deloitte",
    "Deloitte USI": "Deloitte",
    "Deloitte USI Tax": "Deloitte",
    "Accenture": "Accenture",
    "Cognizant": "Cognizant",
    "Wipro": "Wipro",
    "TCS": "Tata Consultancy Services",
    "Tata Consultancy Services": "Tata Consultancy Services",
    "IBM": "IBM",
    "IBM India": "IBM",
    "Acuitas 360": "Acuitas 360",
    "UBS": "UBS",
    "Lyric": "Lyric",
    "eAppSys": "eAppSys",
    "Lntd": "L&T", 
}

# Known Canonical Companies
CANONICAL_COMPANIES = list(set(COMPANY_ALIASES.values()))
