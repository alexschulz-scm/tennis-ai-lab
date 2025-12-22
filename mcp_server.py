from mcp.server.fastmcp import FastMCP
from pdf_generator import convert_md_to_pdf
from video_tools import extract_analysis_frames
import os

# Initialize Server
mcp = FastMCP("Tennis-AI-Tools")

# --- TOOL 1: Video Extraction ONLY ---
@mcp.tool()
def prepare_video_for_analysis(video_filename: str) -> str:
    """
    Extracts frames from a video file into the 'temp_frames' folder.
    Returns the paths of the images extracted.
    """
    base_dir = os.getcwd()
    full_path = os.path.join(base_dir, video_filename)
    
    # Use the smart extractor we built earlier
    result = extract_analysis_frames(full_path, output_dir="temp_frames")
    return str(result)

# --- TOOL 2: PDF Generation ---
@mcp.tool()
def generate_branded_pdf(input_path: str, output_path: str) -> str:
    """
    Converts a Markdown analysis into a PDF.
    """
    base_dir = os.getcwd()
    full_input = os.path.join(base_dir, input_path)
    full_output = os.path.join(base_dir, output_path)

    if not os.path.exists(full_input):
        return f"Error: Input file not found at {input_path}"

    try:
        convert_md_to_pdf(full_input, full_output)
        return f"Success: PDF generated at {output_path}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()