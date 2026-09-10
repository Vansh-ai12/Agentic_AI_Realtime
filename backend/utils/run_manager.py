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
    supabase.table("agent_runs").update({
        "status": status,
        "total_attempts": total_attempts,
        "total_tokens": total_tokens,
        "completed_at": "now()"
    }).eq("id", run_id).execute()