"""
OAuth authentication routes for Gmail and Notion connections.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from db.supabase_client import supabase
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Gmail OAuth configuration
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
GMAIL_REDIRECT_URI = "http://localhost:8000/api/auth/gmail/callback"

# Notion OAuth configuration  
NOTION_CLIENT_ID = os.getenv("NOTION_CLIENT_ID")
NOTION_CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET")
NOTION_REDIRECT_URI = "http://localhost:8000/api/auth/notion/callback"

# Test user ID (in production, this would come from session/auth)
TEST_USER_ID = "c0a65264-dc6c-4198-8e88-7c63c180d1cf"


@router.get("/auth/gmail")
def gmail_auth():
    """Initiate Gmail OAuth flow"""
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Gmail OAuth not configured")
    
    # In production, this would redirect to Google's OAuth URL
    # For now, return a mock response
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GMAIL_CLIENT_ID}&redirect_uri={GMAIL_REDIRECT_URI}&response_type=code&scope=https://www.googleapis.com/auth/gmail.readonly&access_type=offline"
    
    return RedirectResponse(url=auth_url)


@router.get("/auth/gmail/callback")
def gmail_callback(request: Request):
    """Handle Gmail OAuth callback"""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")
    
    # In production, exchange code for access token
    # For now, store a mock connection
    try:
        # Store connection in database
        supabase.table("connections").insert({
            "user_id": TEST_USER_ID,
            "source": "gmail",
            "access_token": "mock_token_" + code[:10],
            "status": "active"
        }).execute()
        
        # Redirect to frontend
        return RedirectResponse(url="http://localhost:3000/connect/gmail?connected=true")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store connection: {str(e)}")


@router.get("/auth/notion")
def notion_auth():
    """Initiate Notion OAuth flow"""
    if not NOTION_CLIENT_ID or not NOTION_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Notion OAuth not configured")
    
    # Notion OAuth URL
    auth_url = f"https://api.notion.com/v1/oauth/authorize?client_id={NOTION_CLIENT_ID}&response_type=code&owner=user&redirect_uri={NOTION_REDIRECT_URI}"
    
    return RedirectResponse(url=auth_url)


@router.get("/auth/notion/callback")
def notion_callback(request: Request):
    """Handle Notion OAuth callback"""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")
    
    # In production, exchange code for access token
    # For now, store a mock connection
    try:
        # Store connection in database
        supabase.table("connections").insert({
            "user_id": TEST_USER_ID,
            "source": "notion",
            "access_token": "mock_token_" + code[:10],
            "status": "active"
        }).execute()
        
        # Redirect to frontend
        return RedirectResponse(url="http://localhost:3000/connect/notion?connected=true")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store connection: {str(e)}")


@router.get("/connections")
def get_connections():
    """Get user's connections"""
    try:
        result = supabase.table("connections").select("*").eq("user_id", TEST_USER_ID).execute()
        return {"connections": result.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch connections: {str(e)}")


@router.delete("/connections/{source}")
def delete_connection(source: str):
    """Delete a connection"""
    try:
        supabase.table("connections").delete().eq("user_id", TEST_USER_ID).eq("source", source).execute()
        return {"message": f"{source} connection deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete connection: {str(e)}")
