from fastapi import APIRouter
from db.supabase_client import supabase

router = APIRouter()

@router.get("/runs/{run_id}/trace")
def get_run_trace(run_id: str):
    run = supabase.table("agent_runs").select("*").eq("id", run_id).execute()
    attempts = supabase.table("agent_attempts").select("*").eq("run_id", run_id).order("attempt_number").execute()
    events = supabase.table("trace_events").select("*").eq("run_id", run_id).order("created_at").execute()
    tokens = supabase.table("token_logs").select("*").eq("run_id", run_id).execute()

    return {
        "run": run.data[0] if run.data else None,
        "attempts": attempts.data,
        "events": events.data,
        "token_logs": tokens.data
    }


@router.get("/runs")
def list_recent_runs(limit: int = 20):
    """So the frontend can show a list of runs to pick from, not just a raw run_id."""
    runs = supabase.table("agent_runs").select("id, query, status, total_attempts, created_at") \
        .order("created_at", desc=True).limit(limit).execute()
    return {"runs": runs.data}