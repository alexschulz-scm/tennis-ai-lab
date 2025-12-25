import os
import time
import json
import re
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from google import genai

# --- NODE 1: THE ANALYST (Strict Calibration Version) ---
def analyze_video(state: AgentState):
    print("--- 🧠 ANALYZING VIDEO ---")
    
    # [Social Media & Search Setup remains the same...]
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

    # --- THE NEW PROMPT ---
    full_prompt = f"""
    You are an elite tennis performance coach.
    
    --- INPUT DATA ---
    TARGET: {state['player_description']}
    DECLARED LEVEL: {state['player_level']}
    NOTES: {state['player_notes']}
    FOCUS: {', '.join(state['focus_areas'])}
    LANGUAGE: {lang_instruction}
    
    --- INSTRUCTIONS ---
    You must output the report in the following STRICT sections. Do not skip any.
    
    ### PHASE 1: CALIBRATION (Internal)
    First, determine the player's handedness (Right vs Left). 
    *CRITICAL:* If the video is selfie-mode/mirrored, adjust your analysis so you do not confuse Forehands with Backhands. 
    Look at the grip: 
    - One hand on bottom = Forehand (usually).
    - Two hands = Backhand (usually).
    
    ### PHASE 2: THE REALITY CHECK (Output this First)
    Start your response with a section titled "## 🎯 Reality Check".
    1. State the **Observed Level** based on visual evidence.
    2. Compare it to the **Declared Level** ({state['player_level']}).
    3. Explain the verdict (e.g., "Technique is Advanced, but consistency is Intermediate").
    
    ### PHASE 3: SHOT LOG
    Create a bulleted list of the shots you see to prove you watched the whole video.
    Format: "- [Timestamp]: [Stroke Type] - [Result/Quality]"
    
    ### PHASE 4: TECHNICAL ANALYSIS
    Provide the {report_label} analysis. Focus on the biomechanics.
    
    {social_add_on}
    {search_instruction}

    --- METADATA ---
    Identify TWO specific moments:
    1. "best_shot": The single best execution.
    2. "fix_shot": The clearest example of the MAIN ISSUE.

    Return the timestamps in this exact JSON format at the very end:
    JSON_DATA: {{
        "best_shot": {{"start": 12, "end": 18, "reason": "Great extension"}},
        "fix_shot": {{"start": 45, "end": 50, "reason": "Late preparation example"}}
    }}
    """
    
    # [API Call remains the same...]
    api_key = os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    # Upload Video
    video_file = client.files.upload(file=state['video_path'])
    
    # Wait for processing
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)
        
    if video_file.state.name == "FAILED":
        return {"analysis_text": "Error: Video processing failed."}

    # Generate
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp", 
        contents=[video_file, full_prompt]
    )
    
    # [Parsing Logic remains the same...]
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
    You are a friendly but professional tennis coach named "Court Lens AI".
    
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