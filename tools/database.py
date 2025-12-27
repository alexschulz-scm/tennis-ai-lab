import os
import streamlit as st
from supabase import create_client

# Initialize Client
@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # Fallback for Streamlit Cloud Secrets
    if not url: url = st.secrets.get("SUPABASE_URL")
    if not key: key = st.secrets.get("SUPABASE_KEY")
    
    if not url or not key:
        return None
    
    return create_client(url, key)

def save_analysis_to_db(email, player_name, video_name, analysis_text, json_data, report_type):
    """Saves the analysis result to the cloud."""
    db = init_supabase()
    if not db: return False
    
    try:
        # 1. Inject Metadata into the JSON blob
        # This allows us to save extra info without changing the database columns
        if json_data is None: json_data = {}
        json_data["report_type"] = report_type

        # 2. Calculate Score
        avg_confidence = 0.0
        if "confidence_log" in json_data and json_data["confidence_log"]:
            scores = [float(x.get("confidence_score", 0)) for x in json_data["confidence_log"]]
            if scores:
                avg_confidence = sum(scores) / len(scores)

        data = {
            "player_email": email,
            "player_name": player_name,
            "video_name": video_name,
            "analysis_text": analysis_text,
            "structured_data": json_data,
            "confidence_score": avg_confidence
        }
        
        db.table("tennis_analyses").insert(data).execute()
        return True
    except Exception as e:
        print(f"❌ DB Save Error: {e}")
        return False

def fetch_history(email):
    """Gets past analyses for a specific user."""
    db = init_supabase()
    if not db: return []
    
    try:
        response = db.table("tennis_analyses").select("*")\
            .eq("player_email", email)\
            .order("created_at", desc=True)\
            .limit(10)\
            .execute()
        return response.data
    except Exception as e:
        print(f"❌ DB Fetch Error: {e}")
        return []