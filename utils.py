import re
import unicodedata

def clean_name(name):
    """Standardizes names for matching (lowercase, removes special chars/accents/teams)."""
    if not isinstance(name, str):
        return ""
        
    # 🚨 NEW: Strip accents and special characters (e.g., Dončić -> Doncic)
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    
    # Remove team tags like (SAS) or (PHI)
    name = re.sub(r'\(.*?\)', '', name)
    
    # Remove suffixes like Jr., Sr., III, etc.
    name = re.sub(r'\s+(Jr\.|Sr\.|II|III|IV)$', '', name, flags=re.I)
    
    # lowercase and strip whitespace
    return name.lower().strip()