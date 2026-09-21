from db.supabase_client import supabase

def create_run(user_id: str, query: str) -> str:
    result = supabase.table("agent_runs").insert({
        "user_id": user_id,
        "query": query,
        "status": "in_progress"
    }).execute()
    return result.data[0]["id"]


def create_attempt(run_id: str, attempt_number: int) -> str:
    result = supabase.table("agent_attempts").insert({
        "run_id": run_id,
        "attempt_number": attempt_number
    }).execute()
    return result.data[0]["id"]


def update_run_status(run_id: str, status: str, total_attempts: int, total_tokens: int = 0):
    if not run_id:
        return
    supabase.table("agent_runs").update({
        "status": status,
        "total_attempts": total_attempts,
        "total_tokens": total_tokens,
        "completed_at": "now()"
    }).eq("id", run_id).execute()


def update_attempt(attempt_id: str, **kwargs):
    if not attempt_id:
        return
    allowed_fields = {
        "planner_subquestions",
        "synthesizer_answer",
        "critic_verdict",
        "critic_reason",
        "tokens_used",
        "latency_ms"
    }
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
    if update_data:
        try:
            supabase.table("agent_attempts").update(update_data).eq("id", attempt_id).execute()
        except Exception as e:
            print(f"[RunManager] Warning: failed to update attempt {attempt_id}: {e}")