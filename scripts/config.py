"""
config.py
Centralized configuration for the Placement Intelligence Data Pipeline.
"""
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

CSV_OUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_OUT_DIR.mkdir(parents=True, exist_ok=True)

# Output Files
NOTICES_CSV = CSV_OUT_DIR / "notices.csv"
PLACEMENTS_CSV = CSV_OUT_DIR / "placements.csv"
STUDENTS_CSV = CSV_OUT_DIR / "students.csv"
COMPANY_PLACEMENT_MASTER_CSV = CSV_OUT_DIR / "company_placement_master.csv"
COMPANY_STATISTICS_CSV = CSV_OUT_DIR / "company_statistics.csv"

# Log Files
PIPELINE_LOG = LOGS_OUT_DIR / "pipeline.log"
DATA_QUALITY_REPORT = LOGS_OUT_DIR / "data_quality_report.txt"
UNKNOWN_COMPANIES_CSV = LOGS_OUT_DIR / "unknown_companies.csv"
DUPLICATE_STUDENTS_CSV = LOGS_OUT_DIR / "duplicate_students.csv"
DUPLICATE_NOTICES_CSV = LOGS_OUT_DIR / "duplicate_notices.csv"
INVALID_ROWS_CSV = LOGS_OUT_DIR / "invalid_rows.csv"

# URL Configs
PDF_BASE_URL = "https://www.cbit.ac.in/wp-content/uploads/2019/12/"
LINKEDIN_SEARCH_BASE = "https://www.linkedin.com/search/results/all/?keywords="

# Fuzzy Matching Config
FUZZY_MATCH_THRESHOLD = 85.0

# Supported Notice Stages (Order by length descending to match longest first)
NOTICE_STAGES = sorted([
    "Online Aptitude Test",
    "Psychometric Assessment",
    "HackerRank Assessment Test",
    "In Person Technical Interview",
    "Personal Interview",
    "Technical Interview",
    "Online Assessment",
    "Written Assessment",
    "Group Discussion",
    "Written Test",
    "Written Exam",
    "Aptitude Test",
    "Coding Test",
    "Coding Assessment",
    "Online Exam",
    "Online Test",
    "Technical Test",
    "HR Interview",
    "Placement Circular",
    "Placement Drive",
    "Face to Face Interview",
    "Final Interview",
    "Interviews",
    "Interview",
    "Discussion",
    "Case Study",
    "Results",
    "Drive",
    "Hackathon",
    "Internship",
    "PPO",
    "PPT",
    "Pre-Placement Talk"
], key=len, reverse=True)

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
    "IBM India": "IBM"
}

# Known Canonical Companies
CANONICAL_COMPANIES = list(set(COMPANY_ALIASES.values()))
