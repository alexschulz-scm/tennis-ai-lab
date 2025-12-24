import os
import time
import json
import re
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from google import genai

# --- NODE 1: THE ANALYST (Stays the Same) ---
def analyze_video(state: AgentState):
    print("--- 🧠 ANALYZING VIDEO ---")
    
    # [Prompt Logic Stays Exactly the Same...]
    social_add_on = ""
    if state.get('creator_mode', False):
        social_add_on = """
        --- SOCIAL MEDIA PACK ---
        Identify 2 "Viral Moments" with Timestamps, Hooks, and Captions.
        """

    search_instruction = """
    FINAL STEP:
    At the very end, output a YouTube Search Query on a new line:
    SEARCH_QUERY: [Tennis Drill for X]
    """

    r_type = state['report_type']
    report_label = "QUICK FIX" if ("Quick" in r_type or "Rápida" in r_type) else "FULL AUDIT"
    
    lang_instruction = "Respond in English" if "English" in state['language'] else "Respond in Portuguese"

    full_prompt = f"""
    You are an elite tennis performance coach.
    TARGET: {state['player_description']}
    LEVEL: {state['player_level']}
    NOTES: {state['player_notes']}
    FOCUS: {', '.join(state['focus_areas'])}
    LANGUAGE: {lang_instruction}
    
    REPORT TYPE: {report_label}
    
    Analyze the video and provide a structured report.
    {social_add_on}
    {search_instruction}

    BONUS: Identify TWO specific moments in the video:
    1. "best_shot": The single best execution (good form/result).
    2. "fix_shot": The clearest example of the MAIN ISSUE you identified in the report.

    Return the timestamps in this exact JSON format at the very end:
    JSON_DATA: {{
        "best_shot": {{"start": 12, "end": 18, "reason": "Great extension"}},
        "fix_shot": {{"start": 45, "end": 50, "reason": "Late preparation example"}}
    }}
    """
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    video_file = client.files.upload(file=state['video_path'])
    
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)
        
    if video_file.state.name == "FAILED":
        return {"analysis_text": "Error: Video processing failed."}

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[video_file, full_prompt]
    )
    
    raw_text = response.text
    structured_data = {}
    
    match_json = re.search(r"JSON_DATA:\s*({.*})", raw_text, re.DOTALL)
    if match_json:
        try:
            structured_data = json.loads(match_json.group(1))
        except:
            print("JSON Parse Error")

    return {
        "analysis_text": raw_text,
        "structured_data": structured_data
    }

# --- NODE 2: THE EMAIL DRAFTER (Updated) ---
def draft_email(state: AgentState):
    print("--- 📧 DRAFTING EMAIL ---")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.7 
    )
    
    is_english = "English" in state['language']
    subject_line = "Tennis Analysis: Your Action Plan 🎾" if is_english else "Análise de Tênis: Seu Plano de Ação 🎾"
    
    # --- FIX IS HERE: We now inject state['analysis_text'] ---
    prompt = f"""
    You are a friendly but professional tennis coach named "Schulz AI".
    
    CONTEXT:
    You just analyzed a video for a player.
    
    Here is the FULL REPORT you generated:
    "{state['analysis_text']}"
    
    TASK:
    Write a short, encouraging email to the player summarizing this report.
    1. Acknowledge their hard work.
    2. Briefly mention the Main Strength (from the report).
    3. Briefly mention the Main Focus Area (from the report).
    4. Tell them to check the attached PDF and Video for details.
    
    LANGUAGE: {state['language']}
    """
    
    response = llm.invoke(prompt)
    
    return {"email_draft": f"Subject: {subject_line}\n\n{response.content}"}

# --- BUILD GRAPH ---
workflow = StateGraph(AgentState)
workflow.add_node("analyst", analyze_video)
workflow.add_node("email_writer", draft_email)
workflow.set_entry_point("analyst")
workflow.add_edge("analyst", "email_writer")
workflow.add_edge("email_writer", END)

app_graph = workflow.compile()