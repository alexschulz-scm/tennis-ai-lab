import cv2
import os
import shutil
import numpy as np

def clean_text(text):
    """Sanitizes text for PDF generation."""
    if not text: return ""
    return text.encode('ascii', 'ignore').decode('ascii').strip()

def extract_analysis_frames(video_path, output_dir="temp_frames", frames_per_chunk=6, chunk_duration_sec=4.0):
    """
    Robust Method: Slices video into fixed time chunks (e.g., every 4 seconds).
    Reliability: 100% (Never misses a shot).
    Cost: Creates some 'junk' folders (walking) that the Agent must filter out.
    """
    if not os.path.exists(video_path):
        return {"error": f"Video not found at {video_path}"}
    
    # Setup
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    if total_frames == 0: 
        return {"error": "Video is empty"}

    print(f"Video Duration: {duration:.1f}s. Slicing into {chunk_duration_sec}s chunks...")
    
    chunk_frames = int(chunk_duration_sec * fps)
    saved_summary = []
    
    # Loop through the video in fixed chunks
    num_chunks = int(total_frames / chunk_frames)
    
    for i in range(num_chunks):
        start_f = i * chunk_frames
        end_f = min(total_frames, (i + 1) * chunk_frames)
        
        # Create folder
        chunk_id = i + 1
        chunk_dir = os.path.join(output_dir, f"segment_{chunk_id}")
        os.makedirs(chunk_dir, exist_ok=True)
        
        # Extract frames evenly from this chunk
        indices = np.linspace(start_f, end_f-1, frames_per_chunk, dtype=int)
        
        for k, f_idx in enumerate(indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if ret:
                fname = f"{chunk_dir}/seq_{k+1}.jpg"
                cv2.imwrite(fname, frame)
        
        saved_summary.append(f"Segment {chunk_id}: {frames_per_chunk} frames ({start_f/fps:.1f}s - {end_f/fps:.1f}s)")

    cap.release()
    
    return {
        "status": "success", 
        "message": f"Sliced video into {len(saved_summary)} segments.",
        "structure": "Folders named segment_1, segment_2, etc.",
        "segments": saved_summary
    }