# tools/video_editor.py

# --- MONKEY PATCH (Keep this!) ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ---------------------------------

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.fx.all import crop, resize
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import tempfile
import cv2
import os
from moviepy.editor import VideoFileClip


def extract_frame(video_path, timestamp, output_filename):
    """Saves a single frame from the video as a JPG."""
    try:
        with VideoFileClip(video_path) as clip:
            # Safety Check: Ensure timestamp is within video limits
            if timestamp > clip.duration:
                timestamp = clip.duration / 2
            if timestamp < 0:
                timestamp = 1
                
            clip.save_frame(output_filename, t=timestamp)
            return output_filename
    except Exception as e:
        print(f"Error extracting frame: {e}")
        return None

def create_watermark_image(text, width, height):
    """
    Creates a transparent PNG image with text using purely Python (Pillow).
    Returns a numpy array readable by MoviePy.
    """
    # Create a transparent canvas (RGBA)
    # We make it the same size as the video frame to make positioning easy
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Load default font (or try to load a system font)
    try:
        # Try 'consola.ttf' (Windows code font) for a "Data/Tech" look.
        # Use size 50 so it's readable on mobile.
        font = ImageFont.truetype("consola.ttf", 50)
    except:
        # Fallback to default ugly font if Arial fails
        font = ImageFont.load_default()

    # Text Settings
    text_content = "COURT LENS AI"
    
    # Calculate text position (Centered horizontally, near bottom)
    # Get bounding box of text
    left, top, right, bottom = draw.textbbox((0, 0), text_content, font=font)
    text_w = right - left
    text_h = bottom - top
    
    x = (width - text_w) / 2
    y = height - 150 # 150 pixels from bottom
    
    # Draw "Shadow" (Black) for readability
    draw.text((x+2, y+2), text_content, font=font, fill=(0, 0, 0, 180))
    # Draw "Main Text" (White)
    draw.text((x, y), text_content, font=font, fill=(255, 255, 255, 230))
    
    return np.array(img)

def create_viral_clip(video_path, start_time, end_time):
    """
    Cuts, Crops to 9:16, Resizes to 1080x1920, and adds Watermark.
    """
    fd, output_path = tempfile.mkstemp(suffix="_viral.mp4")
    os.close(fd)

    video = VideoFileClip(video_path)
    
    try:
        # 1. Validation & Cut (Standard logic)
        start = float(start_time)
        end = float(end_time)
        if start < 0: start = 0
        if end > video.duration: end = video.duration
        if start >= end: raise ValueError("Invalid timestamps")
        
        clip = video.subclip(start, end)
        
        # 2. Crop (9:16)
        w, h = clip.size
        target_ratio = 9/16
        crop_width = int((h * target_ratio) // 2 * 2)
        target_height = int(h // 2 * 2)
        
        x_center = w / 2
        x1 = x_center - (crop_width / 2)
        x2 = x_center + (crop_width / 2)
        
        cropped_clip = crop(clip, x1=x1, y1=0, x2=x2, y2=target_height)
        
        # 3. Resize to HD (1080x1920)
        final_clip = resize(cropped_clip, newsize=(1080, 1920))
        
        # --- NEW STEP: WATERMARK OVERLAY ---
        # Generate the text image
        watermark_array = create_watermark_image("COURT LENS A", 1080, 1920)
        
        # Create a MoviePy clip from that image
        txt_clip = ImageClip(watermark_array).set_duration(final_clip.duration)
        
        # Composite them (Layer Text on top of Video)
        final_composite = CompositeVideoClip([final_clip, txt_clip])
        
        # 4. Write File
        final_composite.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            preset="fast", 
            ffmpeg_params=["-pix_fmt", "yuv420p"], 
            logger="bar" 
        )
            
    finally:
        video.close()
            
    return output_path


def normalize_input_video(input_path):
    """
    Converts iPhone/HEVC videos to standard H.264 MP4 
    so OpenCV and web browsers can read them.
    """
    try:
        # Check if we can read it with OpenCV
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            print("⚠️ OpenCV cannot open video. Converting...")
            needs_conversion = True
        else:
            # Read one frame to be sure
            ret, frame = cap.read()
            if not ret:
                print("⚠️ OpenCV cannot read frames. Converting...")
                needs_conversion = True
            else:
                needs_conversion = False
        cap.release()

        # If it works, just return the original path
        if not needs_conversion:
            return input_path

        # If we need to convert:
        print("🔄 Converting iPhone/HEVC video to Standard MP4...")
        output_path = input_path.replace(".mp4", "_fixed.mp4").replace(".mov", "_fixed.mp4")
        
        clip = VideoFileClip(input_path)
        # Write to H.264 (Standard format)
        clip.write_videofile(output_path, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        clip.close()
        
        print(f"✅ Conversion Complete: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ Conversion Failed: {e}")
        return input_path # Return original as fallback