import re
import logging
from typing import Dict, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# PII Detection Patterns
# Email addresses
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Phone numbers (various formats)
PHONE_PATTERNS = [
    r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # International/US format
    r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Simple US format
    r'\b\d{10}\b',  # 10-digit consecutive
]

# Physical addresses (simplified pattern - catches common patterns)
ADDRESS_PATTERNS = [
    r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Circle|Cir)\b',
    r'\d+\s+[A-Za-z\s]+(?:Apt|Suite|Ste|Unit|#)\s*\d+',
]

# Government ID-like patterns (SSN, passport numbers, etc.)
GOV_ID_PATTERNS = [
    r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',  # SSN-like pattern
    r'\b[A-Z]{2}\d{6}\b',  # Passport-like pattern
    r'\b\d{9}\b',  # Generic 9-digit ID
]

# Credit card-like patterns (Luhn check would be better, but regex catches obvious ones)
CREDIT_CARD_PATTERNS = [
    r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',  # Major card brands
    r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # Generic 16-digit pattern
]

# Risky action patterns (for the stub)
RISKY_ACTION_PATTERNS = [
    r'I\s+(?:will|have|am)\s+(?:send|email|write|transmit|deliver)\s+(?:an?\s+)?(?:email|message)',
    r'I\s+(?:will|have|am)\s+(?:book|reserve|schedule|confirm)\s+(?:a\s+)?(?:flight|hotel|appointment|meeting)',
    r'I\s+(?:will|have|am)\s+(?:delete|remove|erase|destroy)\s+\w+',
    r'I\s+(?:will|have|am)\s+(?:purchase|buy|order|pay\s+for)\s+\w+',
    r'I\s+(?:will|have|am)\s+(?:execute|run|perform)\s+(?:a\s+)?(?:command|action|operation)',
    r'I\s+(?:will|have|am)\s+(?:create|generate|make)\s+(?:a\s+)?(?:account|user|record)',
    r'\[ACTION:\s*\w+\]',  # Action bracket notation
    r'<action\s*\w+>',  # Action tag notation
]


def redact_pii(text: str) -> Tuple[str, Dict[str, List[str]]]:
    """
    Scan text for PII patterns and redact them.
    
    Args:
        text: The text to scan and redact
    
    Returns:
        Tuple of (redacted_text, redaction_details)
        - redacted_text: Text with PII replaced with placeholders
        - redaction_details: Dict with patterns found and counts
    """
    if not text or not isinstance(text, str):
        return text, {}
    
    redacted_text = text
    redaction_details = {
        "emails": [],
        "phones": [],
        "addresses": [],
        "gov_ids": [],
        "credit_cards": []
    }
    
    # Redact emails
    email_matches = re.finditer(EMAIL_PATTERN, redacted_text, re.IGNORECASE)
    for match in email_matches:
        redaction_details["emails"].append(match.group(0))
    redacted_text = re.sub(EMAIL_PATTERN, '[REDACTED-EMAIL]', redacted_text, flags=re.IGNORECASE)
    
    # Redact phone numbers
    for pattern in PHONE_PATTERNS:
        phone_matches = re.finditer(pattern, redacted_text)
        for match in phone_matches:
            redaction_details["phones"].append(match.group(0))
        redacted_text = re.sub(pattern, '[REDACTED-PHONE]', redacted_text)
    
    # Redact addresses
    for pattern in ADDRESS_PATTERNS:
        address_matches = re.finditer(pattern, redacted_text, re.IGNORECASE)
        for match in address_matches:
            redaction_details["addresses"].append(match.group(0))
        redacted_text = re.sub(pattern, '[REDACTED-ADDRESS]', redacted_text, flags=re.IGNORECASE)
    
    # Redact government IDs
    for pattern in GOV_ID_PATTERNS:
        id_matches = re.finditer(pattern, redacted_text)
        for match in id_matches:
            redaction_details["gov_ids"].append(match.group(0))
        redacted_text = re.sub(pattern, '[REDACTED-ID]', redacted_text)
    
    # Redact credit cards
    for pattern in CREDIT_CARD_PATTERNS:
        cc_matches = re.finditer(pattern, redacted_text)
        for match in cc_matches:
            redaction_details["credit_cards"].append(match.group(0))
        redacted_text = re.sub(pattern, '[REDACTED-CARD]', redacted_text)
    
    # Log redactions for observability
    total_redactions = sum(len(items) for items in redaction_details.values())
    if total_redactions > 0:
        logger.info(f"Redacted {total_redactions} PII items: {redaction_details}")
    
    return redacted_text, redaction_details


def detect_risky_actions(text: str) -> Dict[str, any]:
    """
    Detect if text implies real-world actions requiring confirmation.
    This is a stub per the roadmap - just detection and logging, no execution UI.
    
    Args:
        text: The text to scan for risky action language
    
    Returns:
        Dict with:
        - has_risky_action: bool
        - detected_actions: List of detected action patterns
        - details: List of matches found
    """
    if not text or not isinstance(text, str):
        return {
            "has_risky_action": False,
            "detected_actions": [],
            "details": []
        }
    
    detected_actions = []
    details = []
    
    for pattern in RISKY_ACTION_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            detected_actions.append(pattern)
            details.append({
                "pattern": pattern,
                "matched_text": match.group(0),
                "position": match.span()
            })
    
    has_risky = len(detected_actions) > 0
    
    if has_risky:
        logger.warning(f"Detected {len(detected_actions)} risky action patterns: {detected_actions}")
    
    return {
        "has_risky_action": has_risky,
        "detected_actions": detected_actions,
        "details": details
    }


def apply_output_guardrails(text: str) -> Dict[str, any]:
    """
    Apply all output guardrails to a text.
    
    Args:
        text: The text to process
    
    Returns:
        Dict with:
        - processed_text: Text after guardrails applied
        - redaction_details: PII redaction information
        - risky_action_info: Risky action detection information
        - guardrails_applied: List of guardrails that triggered
    """
    if not text or not isinstance(text, str):
        return {
            "processed_text": text,
            "redaction_details": {},
            "risky_action_info": {},
            "guardrails_applied": []
        }
    
    processed_text = text
    guardrails_applied = []
    
    # Apply PII redaction
    redacted_text, redaction_details = redact_pii(processed_text)
    processed_text = redacted_text
    
    total_redactions = sum(len(items) for items in redaction_details.values())
    if total_redactions > 0:
        guardrails_applied.append("pii_redaction")
    
    # Detect risky actions (stub - just detection, no blocking)
    risky_action_info = detect_risky_actions(processed_text)
    if risky_action_info["has_risky_action"]:
        guardrails_applied.append("risky_action_detection")
    
    return {
        "processed_text": processed_text,
        "redaction_details": redaction_details,
        "risky_action_info": risky_action_info,
        "guardrails_applied": guardrails_applied
    }
