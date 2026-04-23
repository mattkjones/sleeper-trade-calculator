import re

def clean_name(name):
    """Standardizes names for matching (lowercase, no special characters/teams)."""
    if not isinstance(name, str):
        return ""
    # Remove team tags like (SAS) or (PHI)
    name = re.sub(r'\(.*?\)', '', name)
    # Remove suffixes like Jr., Sr., III, etc.
    name = re.sub(r'\s+(Jr\.|Sr\.|II|III|IV)$', '', name, flags=re.I)
    # lowercase and strip whitespace
    return name.lower().strip()