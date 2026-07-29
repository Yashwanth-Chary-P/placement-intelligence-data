"""
pdf_parser.py
Phase 2: Extracts student-level placement records from PDFs.
"""
import pdfplumber
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("pdf_parser")

def _generate_match_key(company_name: str) -> str:
    """EXACT match key logic copied from Phase 1 to ensure integrity."""
    if not company_name:
        return ""
    key = str(company_name).lower()
    key = key.replace('&', 'and')
    key = re.sub(r'[^a-z0-9\s]', '', key)
    key = re.sub(r'\s+', ' ', key).strip()
    return key

def parse_package(val: Any) -> Any:
    """Extracts numeric package (CTC) as a float or returns None."""
    if val is None:
        return None
    val_str = str(val)
    match = re.search(r'(\d+(?:\.\d+)?)', val_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def normalize_placement_mode(val: Any) -> str:
    """Normalizes to On Campus / Off Campus."""
    if not val:
        return ""
    v = str(val).lower()
    if 'on' in v:
        return 'On Campus'
    if 'off' in v:
        return 'Off Campus'
    return str(val).strip()

def infer_column_mapping(header_row: List[str]) -> Dict[str, int]:
    """Dynamically detects the columns in a table header."""
    mapping = {}
    for idx, cell in enumerate(header_row):
        if cell is None:
            continue
        norm = str(cell).lower()
        norm = re.sub(r'[^a-z0-9]', '', norm)
        
        if not norm:
            continue
            
        if 'roll' in norm:
            mapping['roll_number'] = idx
        elif 'name' in norm or 'student' in norm:
            mapping['student_name'] = idx
        elif 'company' in norm or 'employer' in norm:
            mapping['company_name'] = idx
        elif 'mode' in norm or 'campus' in norm:
            mapping['placement_mode'] = idx
        elif 'ctc' in norm or 'salary' in norm or 'package' in norm or 'lpa' in norm:
            mapping['package'] = idx
            
    return mapping

def clean_cell_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).replace('\n', ' ').strip()

def process_table(table: List[List[Any]], filename: str, page_num: int, academic_year: str, last_mapping: Dict[str, int] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """Processes a single table and extracts data or logs skipped rows."""
    if not table or len(table) < 2:
        return [], [], last_mapping
        
    header_idx = -1
    mapping = {}
    skipped_rows = []
    
    for i in range(min(5, len(table))):
        row = table[i]
        current_mapping = infer_column_mapping(row)
        if len(current_mapping) >= 3:
            header_idx = i
            mapping = current_mapping
            break
            
    if header_idx == -1:
        if last_mapping:
            mapping = last_mapping
            # We start from row 0 since there's no header
            start_idx = 0 
        else:
            # We can't parse this table, log everything as skipped
            for r in table:
                if any(r):
                    skipped_rows.append({
                        "PDF": filename,
                        "Page": page_num,
                        "Raw extracted content": str(r),
                        "Failure reason": "No valid header found in table and no previous mapping"
                    })
            return [], skipped_rows, None
    else:
        start_idx = header_idx + 1
        
    extracted_rows = []
    
    for i in range(start_idx, len(table)):
        row = table[i]
        if not row:
            continue
            
        if all(not clean_cell_text(cell) for cell in row):
            continue
            
        first_col_text = clean_cell_text(row[0]).lower()
        if 'total' in first_col_text or 'summary' in first_col_text or 'sl.no.' in first_col_text or 'sno' in first_col_text:
            skipped_rows.append({
                "PDF": filename,
                "Page": page_num,
                "Raw extracted content": str(row),
                "Failure reason": "Identified as summary/header row"
            })
            continue
            
        # Check if the row contains typical header words (happens if multi-page tables repeat headers)
        row_str = " ".join([clean_cell_text(c).lower() for c in row if c])
        if 'roll number' in row_str and 'company' in row_str:
            skipped_rows.append({
                "PDF": filename,
                "Page": page_num,
                "Raw extracted content": str(row),
                "Failure reason": "Identified as repeated header row"
            })
            continue
            
        data = {}
        for target, idx in mapping.items():
            if idx < len(row):
                data[target] = clean_cell_text(row[idx])
            else:
                data[target] = ""
                
        company_name = data.get('company_name', '')
        if not company_name and extracted_rows:
            # Inherit from previous row if cell is empty (common in merged PDF cells)
            company_name = extracted_rows[-1]['company_name']
            
        if not company_name:
            skipped_rows.append({
                "PDF": filename,
                "Page": page_num,
                "Raw extracted content": str(row),
                "Failure reason": "Missing company name"
            })
            continue
            
        package_lpa = parse_package(data.get('package'))
        
        confidence = "HIGH"
        if not package_lpa:
            confidence = "MEDIUM"
        
        record = {
            "placement_id": str(uuid.uuid4()),
            "academic_year": academic_year,
            "roll_number": data.get('roll_number', ''),
            "student_name": data.get('student_name', ''),
            "company_name": company_name,
            "company_match_key": _generate_match_key(company_name),
            "package_lpa": package_lpa,
            "placement_mode": normalize_placement_mode(data.get('placement_mode', '')),
            "source_pdf": filename,
            "page_number": page_num,
            "parsing_confidence": confidence
        }
        extracted_rows.append(record)
        
    return extracted_rows, skipped_rows, mapping

class StrategyExtractTablesLoose:
    def extract(self, page):
        return page.extract_tables(table_settings={
            "vertical_strategy": "lines", 
            "horizontal_strategy": "lines",
            "snap_tolerance": 5,
            "join_tolerance": 5,
        })
        
class StrategyExtractTablesText:
    def extract(self, page):
        return page.extract_tables(table_settings={
            "vertical_strategy": "text", 
            "horizontal_strategy": "text",
        })

STRATEGIES = [
    StrategyExtractTablesLoose(),
    StrategyExtractTablesText()
]

def parse_pdf(file_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """Parses a single PDF and returns successful rows, skipped rows, and pages processed."""
    success_rows = []
    skipped_rows = []
    
    # Extract academic year
    ay_match = re.search(r'(\d{4}-\d{2})', file_path.name)
    academic_year = ay_match.group(1) if ay_match else "Unknown"
    
    pages_processed = 0
    current_mapping = None
    
    try:
        with pdfplumber.open(file_path) as pdf:
            pages_processed = len(pdf.pages)
            for page_num, page in enumerate(pdf.pages, 1):
                page_success = False
                
                for strategy in STRATEGIES:
                    tables = strategy.extract(page)
                    if not tables:
                        continue
                        
                    page_successful_rows = []
                    page_skipped_rows = []
                    
                    for table in tables:
                        ext_rows, skip_rows, updated_mapping = process_table(table, file_path.name, page_num, academic_year, current_mapping)
                        page_successful_rows.extend(ext_rows)
                        page_skipped_rows.extend(skip_rows)
                        if updated_mapping:
                            current_mapping = updated_mapping
                        
                    if page_successful_rows or page_skipped_rows:
                        success_rows.extend(page_successful_rows)
                        skipped_rows.extend(page_skipped_rows)
                        page_success = True
                        break
                        
                if not page_success:
                    skipped_rows.append({
                        "PDF": file_path.name,
                        "Page": page_num,
                        "Raw extracted content": "Page failed",
                        "Failure reason": "No tables detected by any strategy"
                    })
                    
    except Exception as e:
        logger.error(f"Failed to parse {file_path.name}: {e}")
        skipped_rows.append({
            "PDF": file_path.name,
            "Page": 0,
            "Raw extracted content": "File failed to open",
            "Failure reason": str(e)
        })
        
    return success_rows, skipped_rows, pages_processed
