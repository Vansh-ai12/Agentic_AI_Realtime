import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # or SUPABASE_KEY, whatever you named it

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)