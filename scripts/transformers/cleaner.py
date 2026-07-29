"""
cleaner.py
Cleans and standardizes extracted fields.
"""
import pandas as pd
import re
import unicodedata

def clean_text(text):
    """Removes non-printable chars, extra spaces, newlines."""
    if pd.isna(text) or text is None:
        return ""
    text = str(text)
    # Remove hidden unicode/accents
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    # Remove newlines and tabs
    text = re.sub(r'[\n\t\r]', ' ', text)
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove some extra punctuation if needed, but let's just strip ends
    return text.strip()

def standardize_placement_mode(mode):
    mode = clean_text(mode).lower()
    if 'on' in mode and 'campus' in mode:
        return 'On Campus'
    elif 'off' in mode and 'campus' in mode:
        return 'Off Campus'
    elif mode:
        return mode.title()
    return 'Unknown'

def standardize_ctc(ctc_str):
    ctc_str = clean_text(ctc_str)
    if not ctc_str:
        return None
    # Remove commas and extract first number
    match = re.search(r'(\d+(\.\d+)?)', ctc_str.replace(',', ''))
    if match:
        try:
            return round(float(match.group(1)), 2)
        except ValueError:
            return None
    return None

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Applies cleaning to the entire dataframe."""
    if df.empty:
        return df
        
    # Clean all string columns
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(clean_text)
            
    if 'placement_mode' in df.columns:
        df['placement_mode'] = df['placement_mode'].apply(standardize_placement_mode)
        
    if 'ctc' in df.columns:
        df['ctc_lpa'] = df['ctc'].apply(standardize_ctc)
        df.drop(columns=['ctc'], inplace=True, errors='ignore')
        
    if 'branch' in df.columns:
        # Title case branches just in case
        df['branch'] = df['branch'].str.upper()
        
    return df
