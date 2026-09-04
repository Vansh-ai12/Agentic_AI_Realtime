from fastapi import APIRouter
from connectors.notion_connector import ingest_notion
from connectors.gmail_connector import ingest_gmail

router = APIRouter()

@router.post("/sync/notion")
def sync_notion(user_id: str, connection_id: str, access_token: str):
    return ingest_notion(user_id, connection_id, access_token)

@router.post("/sync/gmail")
def sync_gmail(user_id: str, connection_id: str, access_token: str):
    return ingest_gmail(user_id, connection_id, access_token)