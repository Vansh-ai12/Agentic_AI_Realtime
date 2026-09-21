import os
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(dotenv_path=env_path)

from utils.groq_client import groq_chat_completion
from db.supabase_client import supabase

class CriteriaEvaluator:
    def __init__(self):
        self.eval_model = "llama-3.1-8b-instant"  # Valid Groq model for evaluation
    
    def evaluate_case(self, case, pipeline_result):
        """
        Evaluate a single eval case against pipeline results
        Returns: dict with 'passed', 'reason', 'details'
        """
        criteria = json.loads(case["expected_answer"])
        evaluation_method = criteria.get("evaluation_method", "llm_evaluator")
        
        if evaluation_method == "llm_evaluator":
            return self._llm_evaluate(case, criteria, pipeline_result)
        elif evaluation_method == "behavioral_check":
            return self._behavioral_evaluate(case, criteria, pipeline_result)
        else:
            return {
                "passed": False,
                "reason": f"Unknown evaluation method: {evaluation_method}",
                "details": {}
            }
    
    def _llm_evaluate(self, case, criteria, pipeline_result):
        """
        Use LLM to evaluate if answer meets criteria
        """
        answer = pipeline_result.get("answer", "")
        if not answer:
            return {
                "passed": False,
                "reason": "No answer generated",
                "details": {}
            }
        
        # Check required content
        # Check required content (accepts if any alternative phrasing matches)
        required_content = criteria.get("required_content", [])
        if required_content:
            matched_keywords = [kw for kw in required_content if kw.lower() in answer.lower()]
            missing_required = [] if matched_keywords else required_content
        else:
            missing_required = []
        
        # Check forbidden content
        forbidden_content = criteria.get("forbidden_content", [])
        found_forbidden = []
        for keyword in forbidden_content:
            if keyword.lower() in answer.lower():
                found_forbidden.append(keyword)
        
        # Quick fail based on content checks
        if missing_required and not criteria.get("must_cite_chunks", False):
            return {
                "passed": False,
                "reason": f"Missing required content: expected one of {required_content}",
                "details": {
                    "missing_required": missing_required,
                    "found_forbidden": found_forbidden
                }
            }
        
        if found_forbidden:
            return {
                "passed": False,
                "reason": f"Found forbidden content: {found_forbidden}",
                "details": {
                    "missing_required": missing_required,
                    "found_forbidden": found_forbidden
                }
            }
        
        # Use LLM for detailed evaluation
        evaluation_prompt = criteria.get("evaluation_prompt", "")
        pass_criteria = criteria.get("pass_criteria", [])
        
        llm_prompt = f"""
You are an evaluator for a RAG system. Evaluate the following answer against the criteria.

ANSWER TO EVALUATE:
{answer}

EVALUATION CRITERIA:
{json.dumps(pass_criteria, indent=2)}

CONTEXT:
{evaluation_prompt}

Return JSON format:
{{
    "passed": true/false,
    "reason": "Brief explanation",
    "met_criteria": ["list of criteria that were met"],
    "failed_criteria": ["list of criteria that were not met"]
}}
"""
        
        try:
            response = groq_chat_completion(
                model=self.eval_model,
                messages=[
                    {"role": "system", "content": "You are an objective evaluator. Return only valid JSON."},
                    {"role": "user", "content": llm_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            llm_result = response.choices[0].message.content.strip()
            evaluation = json.loads(llm_result)
            
            return {
                "passed": evaluation.get("passed", False),
                "reason": evaluation.get("reason", "LLM evaluation failed"),
                "details": {
                    "met_criteria": evaluation.get("met_criteria", []),
                    "failed_criteria": evaluation.get("failed_criteria", []),
                    "missing_required": missing_required,
                    "found_forbidden": found_forbidden
                }
            }
            
        except Exception as e:
            return {
                "passed": False,
                "reason": f"LLM evaluation failed: {str(e)}",
                "details": {
                    "missing_required": missing_required,
                    "found_forbidden": found_forbidden
                }
            }
    
    def _behavioral_evaluate(self, case, criteria, pipeline_result):
        """
        Check pipeline behavior against expected state
        """
        verdict = pipeline_result.get("verdict", "")
        blocked_reason = pipeline_result.get("blocked_reason", "")
        
        # Check expected verdict
        expected_verdict = criteria.get("expected_verdict")
        if expected_verdict and verdict != expected_verdict:
            return {
                "passed": False,
                "reason": f"Expected verdict '{expected_verdict}', got '{verdict}'",
                "details": {
                    "expected_verdict": expected_verdict,
                    "actual_verdict": verdict
                }
            }
        
        # Check blocked reason for adversarial cases
        if expected_verdict == "blocked":
            expected_reason_contains = criteria.get("expected_blocked_reason_contains", [])
            if expected_reason_contains:
                reason_lower = blocked_reason.lower() if blocked_reason else ""
                # Check if ANY of the expected keywords are present (more flexible)
                keyword_found = any(keyword.lower() in reason_lower for keyword in expected_reason_contains)
                if not keyword_found:
                    return {
                        "passed": False,
                        "reason": f"Blocked reason missing expected keywords: {expected_reason_contains}",
                        "details": {
                            "expected_keywords": expected_reason_contains,
                            "actual_reason": blocked_reason
                        }
                    }
        
        # Check PII redaction for edge cases
        if criteria.get("pi_redaction_required"):
            must_contain_redaction_markers = criteria.get("must_contain_redaction_markers", [])
            answer = pipeline_result.get("answer", "")
            for marker in must_contain_redaction_markers:
                if marker not in answer:
                    return {
                        "passed": False,
                        "reason": f"Missing PII redaction marker: {marker}",
                        "details": {
                            "required_markers": must_contain_redaction_markers,
                            "answer_snippet": answer[:200]
                        }
                    }
        
        # Check forbidden content (for PII, etc.)
        forbidden_content = criteria.get("forbidden_content", [])
        if forbidden_content:
            answer = pipeline_result.get("answer", "")
            found_forbidden = []
            for keyword in forbidden_content:
                if keyword.lower() in answer.lower():
                    found_forbidden.append(keyword)
            
            if found_forbidden:
                return {
                    "passed": False,
                    "reason": f"Found forbidden content: {found_forbidden}",
                    "details": {
                        "found_forbidden": found_forbidden
                    }
                }
        
        return {
            "passed": True,
            "reason": "Pipeline behavior matches expected criteria",
            "details": {
                "verdict": verdict,
                "blocked_reason": blocked_reason
            }
        }
