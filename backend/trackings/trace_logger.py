import time
from db.supabase_client import supabase

def log_trace_event(run_id: str, attempt_id: str, node_name: str, input_data: dict, output_data: dict, tokens_used: int = 0, latency_ms: int = 0):
    supabase.table("trace_events").insert({
        "run_id": run_id,
        "attempt_id": attempt_id,
        "node_name": node_name,
        "input": input_data,
        "output": output_data,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms
    }).execute()