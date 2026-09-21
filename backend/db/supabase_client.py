import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

_here = Path(__file__).resolve()
for _env in (_here.parents[2] / ".env.local", _here.parents[1] / ".env.local", Path.cwd() / ".env.local"):
    if _env.exists():
        load_dotenv(dotenv_path=_env, override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # or SUPABASE_KEY, whatever you named it

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)