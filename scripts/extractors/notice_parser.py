"""
notice_parser.py
Parses placement notices from TXT files.
"""
import re
import uuid
import datetime
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Tuple
import urllib.parse
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("notice_parser")

def _parse_date_string(date_str: str) -> Tuple[str, int, str, int]:
    """
    Parses complex date strings like '24 & 25.06.2026' or '01 to 08.04.2026'.
    Returns (iso_date, year, month_name, day) of the first date in the range.
    """
    # Extract the last part which has the month and year
    match = re.search(r'(\d{2})\.(\d{4})', date_str)
    if not match:
        return "", 0, "", 0
    
    month = int(match.group(1))
    year = int(match.group(2))
    
    # Extract the very first number as the day
    day_match = re.search(r'(\d{1,2})', date_str)
    day = int(day_match.group(1)) if day_match else 1
    
    try:
        dt = datetime.date(year, month, day)
        iso_date = dt.isoformat()
        month_name = dt.strftime("%B")
        return iso_date, year, month_name, day
    except ValueError:
        return "", 0, "", 0

def _generate_pdf_url(title: str) -> str:
    """Generates the PDF URL based on the title."""
    # Replace spaces, commas, ampersands, parentheses, hyphens logic
    # Usually standard is replacing spaces with hyphens, removing special chars
    clean_title = re.sub(r'[^\w\s-]', '', title)
    clean_title = re.sub(r'\s+', '-', clean_title)
    url = f"{config.PDF_BASE_URL}{clean_title}.pdf"
    return url

def _detect_stages_and_company(title: str) -> Tuple[str, str]:
    """
    Detects stages from the title based on config.NOTICE_STAGES.
    Infers company name by removing the stages.
    """
    detected_stages = []
    inferred_title = title
    
    for stage in config.NOTICE_STAGES:
        # Case insensitive match with word boundaries if possible, but stage might be multiple words
        # Using simple string replace for now since regex with word boundaries might fail on punctuation
        pattern = re.compile(re.escape(stage), re.IGNORECASE)
        if pattern.search(inferred_title):
            detected_stages.append(stage)
            inferred_title = pattern.sub("", inferred_title)
            
    # Clean up company name (remove extra spaces, commas, '&', 'on', etc. at the end)
    company_name = inferred_title.strip()
    company_name = re.sub(r'(?i)^(the\s+)', '', company_name)
    # Remove trailing words like 'on', 'and', '&', ',', '-'
    company_name = re.sub(r'(?i)\s+(on|and|&|,|-)\s*$', '', company_name).strip()
    
    stages_str = ", ".join(detected_stages)
    return stages_str, company_name

def parse_notice_line(line: str, source: str) -> Dict[str, Any]:
    """Parses a single notice line."""
    line = line.strip()
    if not line:
        return {}
        
    # Date extraction regex: looks for dates at the end
    # Matches patterns like 27.07.2026, 24 & 25.06.2026, 01 to 08.04.2026
    date_regex = r'(\d{1,2}(?:\s*(?:&|to|-|and)\s*\d{1,2})*\.\d{2}\.\d{4})\.?$'
    date_match = re.search(date_regex, line)
    
    date_str = ""
    title = line
    if date_match:
        date_str = date_match.group(1)
        # Remove date and common prefixes like " on " from title
        title = line[:date_match.start()].strip()
        title = re.sub(r'(?i)\s+on\s*$', '', title).strip()
        
    iso_date, year, month, day = _parse_date_string(date_str)
    notice_type, company_name = _detect_stages_and_company(title)
    
    # Generate pdf URL based on original line format if title was modified
    pdf_url = _generate_pdf_url(line)
    
    return {
        "notice_id": str(uuid.uuid4()),
        "company_name": company_name,
        "notice_title": line,  # Keep the full original line as title
        "notice_date": iso_date,
        "year": year,
        "month": month,
        "day": day,
        "notice_type": notice_type,
        "pdf_url": pdf_url,
        "source": source
    }

def process_notices() -> pd.DataFrame:
    """Processes all TXT notices in current and archive directories."""
    logger.info("Starting notice extraction...")
    all_records = []
    
    # Process current notices
    if config.NOTICES_CURRENT_DIR.exists():
        for txt_file in config.NOTICES_CURRENT_DIR.glob("*.txt"):
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    record = parse_notice_line(line, "current")
                    if record:
                        all_records.append(record)
                        
    # Process archive notices
    if config.NOTICES_ARCHIVE_DIR.exists():
        for txt_file in config.NOTICES_ARCHIVE_DIR.glob("*.txt"):
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    record = parse_notice_line(line, "archive")
                    if record:
                        all_records.append(record)
                        
    df = pd.DataFrame(all_records)
    logger.info(f"Extracted {len(df)} raw notices.")
    return df
