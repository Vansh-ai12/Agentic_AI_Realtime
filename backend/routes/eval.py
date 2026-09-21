from fastapi import APIRouter
from db.supabase_client import supabase

router = APIRouter()


@router.get("/eval/results")
def get_eval_results():
    """
    Latest eval_results joined with eval_cases for the D25 dashboard.
    If a case was scored more than once, the newest eval_results row wins.
    """
    cases = supabase.table("eval_cases").select("id, category, query, expected_answer, created_at").execute()
    results = (
        supabase.table("eval_results")
        .select("id, eval_case_id, run_id, passed, notes, created_at")
        .order("created_at", desc=True)
        .execute()
    )

    latest_by_case: dict[str, dict] = {}
    for row in results.data or []:
        cid = row.get("eval_case_id")
        if cid and cid not in latest_by_case:
            latest_by_case[cid] = row

    run_ids = [r["run_id"] for r in latest_by_case.values() if r.get("run_id")]
    token_by_run: dict[str, int] = {}
    verdict_by_run: dict[str, str] = {}
    if run_ids:
        tokens = supabase.table("token_logs").select("run_id, tokens_in, tokens_out").in_("run_id", run_ids).execute()
        for log in tokens.data or []:
            rid = log["run_id"]
            token_by_run[rid] = token_by_run.get(rid, 0) + (log.get("tokens_in") or 0) + (log.get("tokens_out") or 0)
        runs = supabase.table("agent_runs").select("id, status, query").in_("id", run_ids).execute()
        for run in runs.data or []:
            verdict_by_run[run["id"]] = run.get("status") or ""

    rows = []
    for case in cases.data or []:
        result = latest_by_case.get(case["id"])
        run_id = result.get("run_id") if result else None
        rows.append({
            "eval_case_id": case["id"],
            "category": case["category"],
            "query": case["query"],
            "eval_result_id": result["id"] if result else None,
            "run_id": run_id,
            "passed": result["passed"] if result else None,
            "notes": result["notes"] if result else None,
            "scored_at": result["created_at"] if result else None,
            "tokens_used": token_by_run.get(run_id, 0) if run_id else 0,
            "run_status": verdict_by_run.get(run_id) if run_id else None,
        })

    scored = [r for r in rows if r["passed"] is not None]
    passed = [r for r in scored if r["passed"]]
    by_category: dict[str, dict] = {}
    for r in rows:
        cat = r["category"] or "unknown"
        bucket = by_category.setdefault(cat, {"total": 0, "scored": 0, "passed": 0})
        bucket["total"] += 1
        if r["passed"] is not None:
            bucket["scored"] += 1
            if r["passed"]:
                bucket["passed"] += 1

    return {
        "summary": {
            "eval_cases": len(rows),
            "scored": len(scored),
            "passed": len(passed),
            "pass_rate": (len(passed) / len(scored) * 100) if scored else 0.0,
            "by_category": by_category,
        },
        "results": rows,
    }
