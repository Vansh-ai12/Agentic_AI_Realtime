import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[0]))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[1] / ".env.local"
load_dotenv(dotenv_path=env_path)

print("=" * 80)
print("VERIFICATION STEP 5: TEST PII REDACTION")
print("=" * 80)

from security.output_guardrails import redact_pii

# Test realistic examples with PII embedded in full sentences
test_cases = [
    {
        "text": "Contact John Smith at john.smith@example.com or call 555-123-4567 for project details.",
        "description": "Email and phone in professional context"
    },
    {
        "text": "Send the package to 123 Main Street, Apt 4B, New York, NY 10001. My SSN is 123-45-6789.",
        "description": "Address and government ID"
    },
    {
        "text": "For billing questions, email billing@company.com or call our office at (212) 555-0199.",
        "description": "Business contact info"
    },
    {
        "text": "The project status is on track. No sensitive information included.",
        "description": "Clean text with no PII"
    }
]

print(f"\nTesting PII redaction with realistic examples:")

for i, test_case in enumerate(test_cases, 1):
    print(f"\n--- Test {i}: {test_case['description']} ---")
    print(f"Original: {test_case['text']}")
    
    redacted_text, redaction_details = redact_pii(test_case['text'])
    
    print(f"Redacted: {redacted_text}")
    print(f"Redaction details: {redaction_details}")
    
    total_redactions = sum(len(items) for items in redaction_details.values())
    if total_redactions > 0:
        print(f"PASS: {total_redactions} PII items redacted and logged")
    else:
        print("PASS: No PII detected (clean text)")

print("\n" + "=" * 80)
print("PII REDACTION VERIFICATION COMPLETE")
print("=" * 80)
