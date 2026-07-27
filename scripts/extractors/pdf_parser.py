"""
pdf_parser.py
Parses placement report PDFs using pdfplumber, with an abstraction for future OCR support.
"""
import pdfplumber
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("pdf_parser")

class BasePDFParser(ABC):
    """Abstract base class for PDF parsing to support future OCR integrations."""
    
    @abstractmethod
    def parse(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parses a PDF file and returns a list of row dictionaries."""
        pass

class TablePDFParser(BasePDFParser):
    """Parses table-based PDFs using pdfplumber."""
    
    def parse(self, file_path: Path) -> List[Dict[str, Any]]:
        rows = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        # Skip empty tables
                        if not table:
                            continue
                            
                        # Iterate through rows
                        # Assuming first row might be header, let's extract based on column count
                        # Or just blindly take rows and rely on downstream validation
                        # Usually, row looks like: Roll Number, Student Name, Branch, Company, On/Off Campus, CTC
                        for row in table:
                            if not row or len(row) < 7:
                                continue
                                
                            # Basic heuristic to skip headers: check if second column contains 'Roll'
                            if str(row[1]).lower().find('roll') != -1:
                                continue
                                
                            try:
                                roll_no = str(row[1]).strip()
                                student_name = str(row[2]).strip()
                                branch = str(row[3]).strip()
                                company_name = str(row[4]).strip()
                                placement_mode = str(row[5]).strip()
                                
                                # Process CTC which could have text or symbols
                                ctc_str = str(row[6]).strip().replace(',', '')
                                # Extract digits and decimal point
                                ctc_lpa = None
                                import re
                                match = re.search(r'(\d+(\.\d+)?)', ctc_str)
                                if match:
                                    ctc_lpa = float(match.group(1))
                                
                                rows.append({
                                    "roll_no": roll_no,
                                    "student_name": student_name,
                                    "branch": branch,
                                    "company_name": company_name,
                                    "placement_mode": placement_mode,
                                    "ctc_lpa": ctc_lpa
                                })
                            except Exception as e:
                                logger.debug(f"Skipped a malformed row in {file_path.name}: {e}")
                                continue
        except Exception as e:
            logger.error(f"Failed to parse {file_path.name}: {e}")
            raise e
            
        return rows

def process_pdfs() -> Tuple[pd.DataFrame, int]:
    """Processes all PDF reports and returns a dataframe and failure count."""
    logger.info("Starting PDF extraction...")
    
    parser = TablePDFParser()
    all_records = []
    failure_count = 0
    
    if not config.PDF_REPORTS_DIR.exists():
        logger.warning(f"PDF directory not found: {config.PDF_REPORTS_DIR}")
        return pd.DataFrame(), failure_count
        
    for pdf_file in config.PDF_REPORTS_DIR.glob("*.pdf"):
        logger.info(f"Processing PDF: {pdf_file.name}")
        
        # Extract academic year from filename (e.g., 2020-21 or 2024-25)
        import re
        ay_match = re.search(r'(\d{4}-\d{2})', pdf_file.name)
        academic_year = ay_match.group(1) if ay_match else "Unknown"
        
        try:
            rows = parser.parse(pdf_file)
            for row in rows:
                row['academic_year'] = academic_year
                all_records.append(row)
        except Exception as e:
            logger.error(f"Error processing {pdf_file.name}: {e}")
            failure_count += 1
            
    df = pd.DataFrame(all_records)
    logger.info(f"Extracted {len(df)} placement rows from PDFs.")
    return df, failure_count
