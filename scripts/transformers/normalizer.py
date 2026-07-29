"""
normalizer.py
Company name normalization using exact, alias, and fuzzy matching.
"""
import pandas as pd
from rapidfuzz import process, fuzz
from typing import Tuple, Dict, Any
import sys
from pathlib import Path
import re

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts import config
from scripts.utils.logger import get_logger

logger = get_logger("normalizer")

# Global dynamic canonical list
dynamic_canonicals = set(config.CANONICAL_COMPANIES)

def clean_punctuation_for_match(text: str) -> str:
    """Removes trailing punctuation for better matching."""
    return re.sub(r'[,.-]+$', '', str(text)).strip()

def normalize_company_name(name: str) -> Dict[str, Any]:
    """Normalizes a single company name dynamically and returns metadata."""
    original_name = str(name) if pd.notna(name) else ""
    name_clean = clean_punctuation_for_match(original_name)
    
    if not name_clean or len(name_clean) < 2:
        return {
            "normalized": "UNKNOWN",
            "method": "Too Short/Empty",
            "confidence": 0.0,
            "original": original_name
        }
        
    # Stage 1: Alias dictionary (Exact Match overrides)
    for alias, canonical in config.COMPANY_ALIASES.items():
        if name_clean.lower() == alias.lower():
            return {
                "normalized": canonical,
                "method": "Alias Dictionary",
                "confidence": 100.0,
                "original": original_name
            }
            
    # Stage 2: Exact Match against dynamic Canonical Companies
    for canonical in dynamic_canonicals:
        if name_clean.lower() == canonical.lower():
            return {
                "normalized": canonical,
                "method": "Exact Match",
                "confidence": 100.0,
                "original": original_name
            }
            
    # Stage 3: RapidFuzz similarity matching against dynamic canonicals
    if dynamic_canonicals:
        match = process.extractOne(
            name_clean, 
            dynamic_canonicals, 
            scorer=fuzz.WRatio
        )
        
        if match:
            best_match, score, _ = match
            if score >= config.FUZZY_MATCH_THRESHOLD:
                return {
                    "normalized": best_match,
                    "method": "RapidFuzz",
                    "confidence": round(score, 2),
                    "original": original_name
                }
                
    # If we get here, no match was found >= threshold.
    # This is a new valid company. Add it to dynamic canonicals.
    dynamic_canonicals.add(name_clean)
    
    return {
        "normalized": name_clean,
        "method": "New Canonical",
        "confidence": 100.0,
        "original": original_name
    }

def normalize_dataframe(df: pd.DataFrame, source: str, company_col: str = 'company_name') -> Tuple[pd.DataFrame, int]:
    """Applies normalization to a dataframe and logs unknowns and audit metrics."""
    logger.info(f"Normalizing company names in column: {company_col}")
    
    if df.empty or company_col not in df.columns:
        return df, 0
        
    results = [normalize_company_name(val) for val in df[company_col]]
    
    df[company_col] = [res['normalized'] for res in results]
    
    audit_records = [{
        "original_company": res['original'],
        "normalized_company": res['normalized'],
        "matching_method": res['method'],
        "confidence": res['confidence'],
        "source": source
    } for res in results]
    
    # Write audit log
    audit_df = pd.DataFrame(audit_records).drop_duplicates()
    header = not Path(config.COMPANY_NORMALIZATION_AUDIT_CSV).exists()
    audit_df.to_csv(
        config.COMPANY_NORMALIZATION_AUDIT_CSV,
        mode='a',
        index=False,
        header=header
    )
    
    unknowns = df[df[company_col] == 'UNKNOWN']
    unknown_count = len(unknowns)
    
    if not unknowns.empty:
        logger.warning(f"Found {unknown_count} UNKNOWN companies during normalization.")
        
        unknown_audit = [r for r in audit_records if r['normalized_company'] == 'UNKNOWN']
        unknown_audit_df = pd.DataFrame(unknown_audit)
        
        header_unk = not Path(config.UNKNOWN_COMPANIES_CSV).exists()
        unknown_audit_df[['original_company']].drop_duplicates().to_csv(
            config.UNKNOWN_COMPANIES_CSV, 
            mode='a', 
            index=False, 
            header=header_unk
        )
        
    return df, unknown_count
