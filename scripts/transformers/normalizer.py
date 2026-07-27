"""
normalizer.py
Company name normalization using exact, alias, and fuzzy matching.
"""
import pandas as pd
from rapidfuzz import process, fuzz
from typing import Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("normalizer")

def normalize_company_name(name: str) -> str:
    """Normalizes a single company name across 3 stages."""
    name = str(name).strip()
    
    # Stage 1 & 2: Exact match / Alias dictionary
    if name in config.COMPANY_ALIASES:
        return config.COMPANY_ALIASES[name]
        
    for canonical in config.CANONICAL_COMPANIES:
        if name.lower() == canonical.lower():
            return canonical
            
    # Stage 3: RapidFuzz similarity matching
    if config.CANONICAL_COMPANIES:
        match = process.extractOne(
            name, 
            config.CANONICAL_COMPANIES, 
            scorer=fuzz.WRatio
        )
        
        if match:
            # Rapidfuzz extractOne returns (match, score, index)
            best_match, score, _ = match
            if score >= config.FUZZY_MATCH_THRESHOLD:
                return best_match
                
    return "UNKNOWN"

def normalize_dataframe(df: pd.DataFrame, company_col: str = 'company_name') -> Tuple[pd.DataFrame, int]:
    """Applies normalization to a dataframe and logs unknowns."""
    logger.info(f"Normalizing company names in column: {company_col}")
    
    if df.empty:
        return df, 0
        
    original_col = f"original_{company_col}"
    df[original_col] = df[company_col]
    
    df[company_col] = df[company_col].apply(normalize_company_name)
    
    unknowns = df[df[company_col] == 'UNKNOWN']
    unknown_count = len(unknowns)
    
    if not unknowns.empty:
        logger.warning(f"Found {unknown_count} UNKNOWN companies during normalization.")
        header = not Path(config.UNKNOWN_COMPANIES_CSV).exists()
        unknowns[[original_col]].drop_duplicates().to_csv(
            config.UNKNOWN_COMPANIES_CSV, 
            mode='a', 
            index=False, 
            header=header
        )
        
    df = df.drop(columns=[original_col])
    return df, unknown_count
