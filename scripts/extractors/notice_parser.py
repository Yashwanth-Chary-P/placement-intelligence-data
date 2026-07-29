"""
notice_parser.py
Parses placement notices from TXT files for Phase 1.
"""
import re
import datetime
from pathlib import Path
import pandas as pd
from typing import Dict, Any, Tuple
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("notice_parser")

def _parse_date_string(date_str: str) -> Tuple[str, str, str]:
    """
    Parses complex date strings like '24 & 25.06.2026' or '01 to 08.04.2026'.
    Returns (iso_date, year, month_name) of the first date in the range.
    """
    if not date_str:
        return "", "", ""
        
    # Extract the last part which has the month and year
    match = re.search(r'(\d{2})\.(\d{4})', date_str)
    if not match:
        return "", "", ""
    
    month = int(match.group(1))
    year = int(match.group(2))
    
    # Extract the very first number as the day
    day_match = re.search(r'(\d{1,2})', date_str)
    day = int(day_match.group(1)) if day_match else 1
    
    try:
        dt = datetime.date(year, month, day)
        iso_date = dt.isoformat()
        month_name = dt.strftime("%B")
        return iso_date, str(year), month_name
    except ValueError:
        return "", "", ""

def _generate_pdf_url(title: str) -> str:
    """Generates the PDF URL based on the original title."""
    clean_title = re.sub(r'[^\w\s-]', '', title)
    clean_title = re.sub(r'\s+', '-', clean_title)
    url = f"{config.PDF_BASE_URL}{clean_title}.pdf"
    return url

def _generate_match_key(company_name: str) -> str:
    """Generates a highly normalized match key for future joining."""
    if not company_name:
        return ""
        
    key = str(company_name).lower()
    key = key.replace('&', 'and')
    # Remove all punctuation except alphanumeric and spaces
    key = re.sub(r'[^a-z0-9\s]', '', key)
    # Collapse multiple spaces
    key = re.sub(r'\s+', ' ', key).strip()
    return key

def _detect_stages_and_company(title: str) -> Tuple[str, bool]:
    """
    Detects the earliest occurrence of any known stage keyword.
    Returns (company_name, stage_found_boolean).
    Preserves company qualifiers and internal parentheses.
    """
    lowest_idx = len(title)
    stage_found = False
    
    for stage in config.NOTICE_STAGES:
        pattern = re.compile(r'(?i)(?<!\w)' + re.escape(stage) + r'(?!\w)')
        for m in pattern.finditer(title):
            if m.start() < lowest_idx:
                lowest_idx = m.start()
                stage_found = True

    if lowest_idx == len(title):
        company_name = title
    else:
        company_name = title[:lowest_idx]
        
    # Gentle trimming: ONLY remove leading 'the' and trailing 'on', 'and', '&', ',', '-'
    company_name = company_name.strip()
    company_name = re.sub(r'(?i)^(the\s+)', '', company_name)
    company_name = re.sub(r'(?i)\s+(on|and)\s*$', '', company_name).strip()
    company_name = re.sub(r'[\s,&,\-,\–]+$', '', company_name).strip()
    
    return company_name, stage_found

def parse_notice_line(line: str, source: str) -> Dict[str, Any]:
    """Parses a single notice line strictly adhering to Phase 1 rules."""
    line = line.strip()
    if not line:
        return {}
        
    # Date extraction regex anchored to the end of the line
    date_regex = r'(\d{1,2}(?:\s*(?:&|to|-|and)\s*\d{1,2})*\.\d{2}\.\d{4})\.?$'
    date_match = re.search(date_regex, line)
    
    date_str = ""
    title_without_date = line
    date_found = False
    
    if date_match:
        date_str = date_match.group(1)
        date_found = True
        # Strip the date and any trailing " on " from the title
        title_without_date = line[:date_match.start()].strip()
        title_without_date = re.sub(r'(?i)\s+on\s*$', '', title_without_date).strip()
        
    iso_date, year, month = _parse_date_string(date_str)
    
    company_name, stage_found = _detect_stages_and_company(title_without_date)
    company_match_key = _generate_match_key(company_name)
    pdf_url = _generate_pdf_url(line)
    
    # Confidence Scoring
    if stage_found and date_found:
        confidence = "HIGH"
    elif date_found and not stage_found:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
        
    return {
        "company_name": company_name,
        "company_match_key": company_match_key,
        "notice_date": iso_date,
        "year": year,
        "month": month,
        "source": source,
        "pdf_url": pdf_url,
        "original_title": line,
        "parsing_confidence": confidence
    }

def process_notices() -> pd.DataFrame:
    """Processes all TXT notices strictly for Phase 1 output."""
    logger.info("Starting production-grade notice extraction...")
    all_records = []
    
    if config.NOTICES_CURRENT_DIR.exists():
        for txt_file in config.NOTICES_CURRENT_DIR.glob("*.txt"):
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    record = parse_notice_line(line, "current")
                    if record:
                        all_records.append(record)
                        
    if config.NOTICES_ARCHIVE_DIR.exists():
        for txt_file in config.NOTICES_ARCHIVE_DIR.glob("*.txt"):
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    record = parse_notice_line(line, "archive")
                    if record:
                        all_records.append(record)
                        
    df = pd.DataFrame(all_records)
    logger.info(f"Successfully processed {len(df)} notices.")
    return df
