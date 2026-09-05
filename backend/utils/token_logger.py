from db.supabase_client import supabase

def log_tokens(run_id: str, attempt_id: str, agent_role: str, model: str, tokens_in: int, tokens_out: int):
    """Logs token usage for a single agent call to Supabase."""
    supabase.table("token_logs").insert({
        "run_id": run_id,
        "attempt_id": attempt_id,
        "agent_role": agent_role,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out
    }).execute()