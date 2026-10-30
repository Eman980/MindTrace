from typing import List, Dict, Any, Tuple
from app.config import settings

def calculate_misconception_severity(evidence_points: List[int]) -> Tuple[int, str]:
    """
    Calculate the cumulative severity score and assign a severity level
    based on transparent FYP-1 rubrics:
    0 - 2: Low Priority
    3 - 5: Medium Priority
    6+:    High Priority
    """
    total_score = sum(evidence_points)
    
    if total_score <= settings.SEVERITY_LOW_MAX:
        level = "Low"
    elif total_score <= settings.SEVERITY_MED_MAX:
        level = "Medium"
    else:
        level = "High"
        
    return total_score, level

def get_signal_weight(signal_type: str, custom_weight: int = None) -> int:
    """
    Returns standard point weights for misconception signals.
    """
    if custom_weight is not None:
        return custom_weight
        
    weights = {
        "explicit_checkpoint": settings.POINT_INCORRECT_CHECKPOINT,      # +2
        "explicit_vague": settings.POINT_VAGUE_CHECKPOINT,                # +1
        "behavioural_replay": settings.POINT_REPLAY_EXCEEDED,             # +2
        "manual_unresolved": settings.POINT_MARKED_UNRESOLVED,            # +3
        "conversational_pattern": settings.POINT_REPEATED_CONFUSION,      # +2
    }
    return weights.get(signal_type, 2)
