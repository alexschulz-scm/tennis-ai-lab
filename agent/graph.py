import os
import time
import json
import re
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AgentState
from google import genai

# --- NODE 1: THE ANALYST (Template Version) ---
def analyze_video(state: AgentState):
    print("--- 🧠 ANALYZING VIDEO ---")
    
    # --- 🛠️ DEV MODE BYPASS ---
    if state.get("dev_mode"):
        print("⚡ SKIPPING AI CALL (DEV MODE)")
        time.sleep(2) 
        
        # Hardcoded Dummy Response (Updated with Confidence Log)
        dummy_response = """
        ## 🎯 Reality Check
        **Observed Level:** Intermediate (NTRP 3.5)
        **Reasoning:**
        * Good consistency on rally balls.
        * Footwork breaks down when forced wide.

        ## 🧬 Biomechanical Audit
        **The Good (Strengths):**
        * Solid contact point in front of body.
        * Good racquet head speed.

        **The Bad (Major Flaws):**
        * Left arm drops too early (loss of balance).
        * Stance is too open on approach shots.

        ## 🛠️ The Fix (Action Plan)
        **Correction:** Keep the left hand up longer to track the ball.
        **Drill:** "The Handcuff Drill" - Keep hands together during unit turn.

        SEARCH_QUERY: Tennis Unit Turn Drills
        
        JSON_DATA: {
            "best_shot": {"start": 2, "end": 5, "key_moment": 4, "reason": "Perfect extension"},
            "fix_shot": {"start": 8, "end": 11, "key_moment": 9, "reason": "Dropped left arm"},
            "confidence_log": [
                {"claim": "Left arm drops too early", "evidence": "Frame at 0:09 shows distinct drop before contact.", "confidence_score": 9.2, "visibility_status": "CLEAR"},
                {"claim": "Stance is too open", "evidence": "Feet position clearly visible at 0:10.", "confidence_score": 8.5, "visibility_status": "CLEAR"}
            ]
        }
        """
        return {
            "analysis_text": dummy_response,
            "structured_data": {
                "best_shot": {"start": 2, "end": 5, "key_moment": 4, "reason": "Perfect extension"},
                "fix_shot": {"start": 8, "end": 11, "key_moment": 9, "reason": "Dropped left arm"},
                "confidence_log": [
                    {"claim": "Left arm drops too early", "confidence_score": 9.2},
                    {"claim": "Stance is too open", "confidence_score": 8.5}
                ]
            }
        }
    # ----------------------------------
    # DEBUG: Print inputs to Terminal to verify data is arriving
    player_hand = state.get('handedness', 'Right')
    stroke_context = state.get('stroke_type', 'Match Play') # <--- Check this line in logs
    player_level = state.get('player_level')
   
    # --- REAL AI LOGIC ---
    print("🤖 CALLING GEMINI API...")

    # 1. Setup Creator Mode
    social_add_on = ""
    if state.get('creator_mode', False):
        social_add_on = """
        ## 📱 Content Creator Pack
        **Viral Hook:** [Write a catchy 3-second hook for Reels]
        **Caption:** [Write a short, engaging caption]
        **Hashtags:** [List 5 relevant tags]
        """

    # 2. Setup Context & Language
    lang_instruction = "Respond in English" if "English" in state['language'] else "Respond in Portuguese"
    player_hand = state.get('handedness', 'Right')
    stroke_context = state.get('stroke_type', 'Match Play')
    
    # 3. Handle Stroke Logic (Prevent Hallucinations)
    stroke_instruction = ""
    if stroke_context != "Match Play / Rally (Mixed)":
        stroke_instruction = f"CRITICAL CONTEXT: The user has confirmed this video contains (may no be EXCLUSIVELY) **{stroke_context}**. Identify all the {stroke_context} and use all the {stroke_context} strokes in the video for your analysis."


    # 4. Handle Report Type (Dynamic Template)
    r_type = state['report_type']
    
    if "Quick" in r_type or "Rápida" in r_type:
        # --- TEMPLATE A: QUICK FIX ---
        analysis_instruction = "Focus on the SINGLE most important technical flaw. Be concise and direct."
        analysis_template = """
        ## 🎯 Reality Check
        **Observed Level:** 
        [Identify the real player level. You can use the NTRP scale]

        **Reasoning:** 
        [Explain the gap between Declared Level vs The level that you evaluated for the player. Mention all relavant components for the level that you determined (consistency, footwork, biomechanics complexity, and any other relevant perspective).]

        ## ⚡ Quick Fix Analysis
        **The Main Issue:** 
        [Identify the one biggest thing holding them back]

        **The Fix:** 
        [Specific biomechanical correction]

        **One Drill:** 
        [Name one specific drill to practice]
        
        
        """
    else:
        # --- TEMPLATE B: FULL AUDIT ---
        analysis_instruction = "Provide a comprehensive, deep-dive biomechanical audit. Analyze strengths, weaknesses, and long-term potential."
        analysis_template = """
        ## 🎯 Reality Check & Level
        **Observed Level:** 
        [Identify the real player level. You can use the NTRP scale. Only consider what you see on the video to define the real player level (Do not be influenced by the player level provided by the user)]

        **Reasoning:** 
        [Explain the gap between Declared Level vs The level that you evaluated for the player. Mention all relavant components for the level that you determined (consistency, footwork, biomechanics complexity, and any other relevant perspective).Only consider what you see on the video to define the real player level (Do not be influenced by the player level provided by the user)]
        
        ## 🧬 Biomechanical Audit
        **The Good (Strengths):**
        * [Point 1]
        * [Point 2]
        * [Point 3]
        
        **The Bad (Major Flaws):**
        * [Point 1 - Be specific about body parts]
        * [Point 2]
        * [Point 3]
        
        ## 🛠️ The Fix (Action Plan)
        **Correction:** 
        [Explain exactly how to move differently]

        **Drill:** 
        [Name a specific drill]
        
        ## 📸 Shot Log
        (List timestamps on separate lines)
        * [Timestamp] [Stroke] [quality]
        * [Timestamp] [Stroke] [quality]
        """

    # --- THE MASTER PROMPT ---
    full_prompt = f"""
    You are an elite tennis performance coach (ATP Level).
    
    --- CONTEXT ---
    TARGET: {state['player_description']}
    DECLARED LEVEL: {state['player_level']}
    DOMINANT HAND: {player_hand}
    STROKE TYPE: {stroke_context}
    NOTES: {state['player_notes']}
    LANGUAGE: {lang_instruction}
    
    ### CONFIDENCE & VERIFICATION PROTOCOL
    You are a precision instrument, not a creative writer. Your analysis must be based strictly on VISIBLE EVIDENCE. Do not hallucinate biomechanics that are obscured by blur, framing, or occlusion.

    1. The "Visual Audit" Step
    Before analyzing any stroke, you must internally calculate a `Visibility_Score` (0-10) for:
    - Racquet Face: Is the angle clear at contact?
    - Footwork: Are the feet fully in frame?
    - Grip: Is the hand position clearly distinguishable?

    2. The Confidence Threshold Rule
    - Threshold: 8.0 / 10.
    - Rule: If confidence in a specific observation is below 8.0, YOU MUST DISCARD IT. Better to be silent than wrong.

    3. Handling Ambiguities:
    - Occlusion: If body blocks contact, do NOT guess.
    - Motion Blur: Describe path, not exact angle.
    - Frame Rate: Do not estimate exact spin rate if frames are missing.

    --- INSTRUCTIONS ---
    Consider the player level in you analysis and language. Be be didactic in your explanation. Be honest but try to provide information in a way that keeps player motivated to improve and not gave up of trying new analysis because of harsh message  
    {stroke_instruction}
    {analysis_instruction}
    
    IMPORTANT: Use BULLET POINTS and NEW LINES. 
    
    --- OUTPUT TEMPLATE (Follow this Exactly) ---
    {analysis_template}
    
    
    {social_add_on}
    
    SEARCH_QUERY: [YouTube Search Term for the Drill]
    
    --- METADATA (Hidden) ---
    Generate a STRICT JSON block at the very end. 
    RULES:
    1. Keys must be "best_shot" and "fix_shot".
    2. "start", "end", and "key_moment" must be INTEGERS (Seconds).
    3. Do not add markdown or comments inside the JSON.
    4. "key_moment" is an integer (second) pinpointing the EXACT moment the flaw or good form is most visible.
    5. The "reason" MUST be unique to this specific video analysis. DO NOT COPY THE EXAMPLES.
    
    JSON_DATA: {{
        "best_shot": {{"start": <int>, "end": <int>, "key_moment": <int>, "reason": "<Insert Reason>"}},
        "fix_shot": {{"start": <int>, "end": <int>, "key_moment": <int>, "reason": "<Insert Reason>"}},
        "confidence_log": [
            {{
                "claim": "<Brief Claim 1>", 
                "evidence": "<Frame/Visual Proof>", 
                "confidence_score": <float 0-10>, 
                "visibility_status": "<CLEAR/PARTIAL>"
            }}
        ]
    }}
    """
    
    # [API Call - Keep Exactly the Same]
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
    
    # [Parsing - Keep Exactly the Same]
    raw_text = response.text
    structured_data = {}
    # Updated Regex to be more robust for JSON extraction
    match_json = re.search(r"JSON_DATA:\s*({.*})", raw_text, re.DOTALL)
    if match_json:
        try:
            structured_data = json.loads(match_json.group(1))
        except: 
            print("⚠️ JSON Parsing Failed. AI might have returned invalid format.")

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