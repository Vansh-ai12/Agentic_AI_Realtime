import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from db.supabase_client import supabase
from rag.chunking import chunk_text
from rag.embeddings import get_embedding
from datetime import datetime, timezone

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "token.json")


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_gmail_messages(max_results: int = 10) -> list[dict]:
    service = get_gmail_service()
    results = service.users().messages().list(userId="me", maxResults=max_results).execute()
    messages = results.get("messages", [])

    emails = []
    for msg_ref in messages:
        msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()

        headers = msg["payload"].get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        internal_date_raw = msg.get("internalDate")
        internal_date = datetime.fromtimestamp(
    int(internal_date_raw) / 1000, tz=timezone.utc
).isoformat() if internal_date_raw else None

        body = extract_body(msg["payload"])

        emails.append({
            "external_id": msg["id"],
            "title": subject,
            "raw_content": body,
            "source_updated_at": internal_date
        })
    return emails


def extract_body(payload) -> str:
    if "parts" in payload:
        text_parts = []
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                data = part["body"]["data"]
                text_parts.append(base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore"))
            elif "parts" in part:
                text_parts.append(extract_body(part))
        return "\n".join(text_parts)
    else:
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""


def ingest_gmail(user_id: str, connection_id: str, max_results: int = 10):
    emails = fetch_gmail_messages(max_results)
    ingested_count = 0

    for email in emails:
        if not email["raw_content"].strip():
            continue

        existing = supabase.table("documents").select("id, source_updated_at") \
            .eq("connection_id", connection_id) \
            .eq("external_id", email["external_id"]).execute()

        if existing.data and existing.data[0]["source_updated_at"] == email["source_updated_at"]:
            continue

        doc_result = supabase.table("documents").upsert({
            "user_id": user_id,
            "connection_id": connection_id,
            "source": "gmail",
            "external_id": email["external_id"],
            "title": email["title"],
            "raw_content": email["raw_content"],
            "source_updated_at": email["source_updated_at"]
        }, on_conflict="connection_id,external_id").execute()

        document_id = doc_result.data[0]["id"]

        supabase.table("chunks").delete().eq("document_id", document_id).execute()

        chunks = chunk_text(email["raw_content"])
        for idx, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            supabase.table("chunks").insert({
                "document_id": document_id,
                "chunk_index": idx,
                "content": chunk,
                "embedding": embedding
            }).execute()

        ingested_count += 1

    supabase.table("connections").update({"last_synced_at": "now()"}) \
        .eq("id", connection_id).execute()

    return {"emails_ingested": ingested_count}