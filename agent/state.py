from typing import TypedDict, List, Optional

class AgentState(TypedDict):
    """
    The 'Clipboard' that travels through the assembly line.
    Every node (AI, Video Tool, PDF Tool) reads/writes to this.
    """
    # INPUTS (From the User)
    video_path: str
    player_description: str
    player_level: str
    player_notes: str
    focus_areas: List[str]
    handedness: str
    stroke_type: str
    report_type: str
    language: str
    creator_mode: bool
    dev_mode: bool           # <--- THIS MUST BE HERE
    
    # INTERMEDIATE DATA (Created by AI)
    analysis_text: Optional[str] = None
    structured_data: Optional[dict] = None # Holds the JSON (timestamps, etc)
    search_query: Optional[str] = None
    
    # OUTPUTS (Created by Tools)
    pdf_path: Optional[str] = None
    viral_clip_paths: List[str] = [] # Stores paths to generated reels
    email_draft: Optional[str] = None
    
    # ERROR HANDLING
    error: Optional[str] = None