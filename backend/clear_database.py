"""
Script to clear all data from Supabase database while preserving schema.
Run with: python clear_database.py
"""

from db.supabase_client import supabase

def clear_table(table_name):
    """Clear all rows from a table"""
    try:
        result = supabase.table(table_name).select("*").execute()
        count = len(result.data) if result.data else 0
        if count > 0:
            # Delete all rows
            supabase.table(table_name).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            print(f"[OK] Cleared {count} rows from {table_name}")
        else:
            print(f"[SKIP] {table_name} already empty")
    except Exception as e:
        print(f"[ERROR] Failed to clear {table_name}: {str(e)}")

def main():
    print("=" * 60)
    print("CLEARING SUPABASE DATABASE DATA")
    print("=" * 60)
    
    # Clear in dependency order (child tables first)
    tables_to_clear = [
        "token_logs",
        "trace_events", 
        "agent_attempts",
        "eval_results",
        "agent_runs",
        "chunks",
        "documents",
        "memory_short_term",
        "memory_long_term",
        "connections",
        "eval_cases",
    ]
    
    for table in tables_to_clear:
        clear_table(table)
    
    print("=" * 60)
    print("DATABASE CLEARING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
