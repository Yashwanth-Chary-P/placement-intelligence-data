"""
logger.py
Structured logging configuration for the pipeline.
"""
import logging
import sys
from pathlib import Path

# Add scripts directory to path to allow importing config
sys.path.append(str(Path(__file__).resolve().parent.parent))
import config

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # File handler
        try:
            fh = logging.FileHandler(config.PIPELINE_LOG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            print(f"Warning: Could not create file handler for logging: {e}")
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger
