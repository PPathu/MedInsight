import logging
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default criteria configurations
DEFAULT_CRITERIA = {
    "qSOFA": {
        "name": "qSOFA",
        "description": "Quick Sequential Organ Failure Assessment",
        "criteria": [
            "- Respiratory Rate (RR) ≥ 22 breaths/min",
            "- Systolic Blood Pressure (SBP) ≤ 100 mmHg",
            "- Altered mentation (GCS verbal response is not \"Oriented\")"
        ],
        "threshold": "≥2 => qSOFA"
    },
    "SIRS": {
        "name": "SIRS",
        "description": "Systemic Inflammatory Response Syndrome",
        "criteria": [
            "- Temperature >38°C or <36°C",
            "- Heart rate >90/min",
            "- Respiratory rate >20/min or PaCO2 <32 mmHg",
            "- White blood cell count >12,000/mm³ or <4,000/mm³ or >10% immature bands"
        ],
        "threshold": "≥2 => SIRS"
    },
    "Sepsis-3": {
        "name": "Sepsis-3",
        "description": "Sepsis-3 Definition",
        "criteria": [
            "- Suspected or documented infection",
            "- Acute increase in SOFA score ≥2 points",
            "- qSOFA ≥2 (in patients outside the ICU)"
        ],
        "threshold": "All criteria met => Sepsis-3"
    }
}

# Active criteria - default to qSOFA
ACTIVE_CRITERIA_KEY = "qSOFA"

# Custom user-defined criteria
CUSTOM_CRITERIA = {}

def get_criteria_list() -> List[Dict]:
    """Get a list of all available criteria including default and custom ones"""
    all_criteria = {}
    all_criteria.update(DEFAULT_CRITERIA)
    all_criteria.update(CUSTOM_CRITERIA)
    return [
        {"key": key, "name": data["name"], "description": data["description"]} 
        for key, data in all_criteria.items()
    ]

def get_active_criteria() -> Dict:
    """Get the currently active criteria configuration"""
    # First check custom criteria
    if ACTIVE_CRITERIA_KEY in CUSTOM_CRITERIA:
        return CUSTOM_CRITERIA[ACTIVE_CRITERIA_KEY]
    # Then check default criteria
    if ACTIVE_CRITERIA_KEY in DEFAULT_CRITERIA:
        return DEFAULT_CRITERIA[ACTIVE_CRITERIA_KEY]
    # Fallback to qSOFA if key not found
    return DEFAULT_CRITERIA["qSOFA"]

def set_active_criteria(criteria_key: str) -> bool:
    """Set the active criteria by key"""
    global ACTIVE_CRITERIA_KEY
    
    # Check if key exists in any criteria set
    if criteria_key in DEFAULT_CRITERIA or criteria_key in CUSTOM_CRITERIA:
        ACTIVE_CRITERIA_KEY = criteria_key
        logger.info(f"Active criteria set to: {criteria_key}")
        return True
    
    logger.error(f"Criteria key not found: {criteria_key}")
    return False

def add_custom_criteria(key: str, name: str, description: str, criteria: List[str], threshold: str) -> bool:
    """Add a new custom criteria configuration"""
    global CUSTOM_CRITERIA
    
    if key in DEFAULT_CRITERIA:
        logger.warning(f"Cannot override default criteria key: {key}")
        return False
    
    # Store threshold exactly as provided by the user
    # The reasoner will use it if it's not empty
    CUSTOM_CRITERIA[key] = {
        "name": name,
        "description": description,
        "criteria": criteria,
        "threshold": threshold or ""  # Store empty string if None
    }
    
    logger.info(f"Added custom criteria: {key} with threshold: '{threshold or ''}'")
    return True

def delete_custom_criteria(key: str) -> bool:
    """Delete a custom criteria configuration"""
    global CUSTOM_CRITERIA, ACTIVE_CRITERIA_KEY
    
    if key not in CUSTOM_CRITERIA:
        logger.warning(f"Custom criteria not found: {key}")
        return False
    
    # If active criteria is being deleted, reset to default
    if ACTIVE_CRITERIA_KEY == key:
        ACTIVE_CRITERIA_KEY = "qSOFA"
        logger.info(f"Active criteria reset to default: {ACTIVE_CRITERIA_KEY}")
    
    del CUSTOM_CRITERIA[key]
    logger.info(f"Deleted custom criteria: {key}")
    return True 
