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
import subprocess
import imageio_ffmpeg
from moviepy.editor import VideoFileClip, vfx

# 1. FIND FFMPEG AUTOMATICALLY
# This finds the ffmpeg.exe that MoviePy installed, so you don't need to install it manually.
FFMPEG_BINARY = imageio_ffmpeg.get_ffmpeg_exe()

def get_rotation(video_path):
    """
    Robust Rotation Detector: Scans ALL metadata for rotation flags.
    """
    try:
        # Check if ffprobe is next to ffmpeg
        ffprobe_binary = FFMPEG_BINARY.replace("ffmpeg", "ffprobe")
        if not os.path.exists(ffprobe_binary):
            # Fallback to system command if not found locally
            ffprobe_binary = "ffprobe"

        cmd = [
            ffprobe_binary, 
            "-v", "quiet", 
            "-print_format", "json", 
            "-show_streams", 
            "-show_format", 
            video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        data = json.loads(result.stdout)

        for stream in data.get('streams', []):
            tags = stream.get('tags', {})
            if 'rotate' in tags:
                return int(float(tags['rotate']))
            
            side_data = stream.get('side_data_list', [])
            for item in side_data:
                if 'rotation' in item:
                    return int(float(item['rotation']))
        return 0
    except Exception as e:
        print(f"⚠️ Rotation Detection Failed: {e}")
        return 0

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

def extract_frame(video_path, timestamp, output_path):
    try:
        cap = cv2.VideoCapture(video_path)
        # Convert seconds to milliseconds
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(output_path, frame)
            cap.release()
            return output_path
        cap.release()
        return None
    except:
        return None

def normalize_input_video(input_path):
    try:
        print(f"🔄 Checking video: {input_path}")
        output_path = input_path.rsplit(".", 1)[0] + "_fixed.mp4"
        
        # 1. Detect Rotation
        rotation = get_rotation(input_path)
        print(f"📐 Detected Rotation Flag: {rotation}°")
        
        # 2. THE NUCLEAR FIX: HARD TRANSPOSE via FFmpeg
        vf_command = ""
        
        if rotation == 90:
            print("🔧 Hard-Fixing 90° Rotation (Transpose)...")
            vf_command = "transpose=1" 
        elif rotation == 180:
            vf_command = "transpose=2,transpose=2"
        elif rotation == 270:
            vf_command = "transpose=2" 

        # Build the command
        cmd = [
            FFMPEG_BINARY,
            "-y",               # Overwrite output
            "-i", input_path,   # Input
            "-c:v", "libx264",  # Video Codec
            
            # --- COMPRESSION FIX ---
            "-preset", "medium", # Slower than 'ultrafast', but MUCH smaller file size
            "-crf", "23",        # Constant Rate Factor (23 is standard high quality, low size)
            "-pix_fmt", "yuv420p", # Ensure web compatibility
            
            "-c:a", "aac"       # Audio Codec
        ]
        
        if vf_command:
            cmd.extend(["-vf", vf_command])
            cmd.extend(["-metadata:s:v:0", "rotate=0"]) 
        
        cmd.append(output_path)
        
        # 3. Execute
        print(f"⚡ Rebuilding Video Pixels: {' '.join(cmd)}")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if os.path.exists(output_path):
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ Video Normalized: {output_path} ({file_size_mb:.1f} MB)")
            return output_path
        else:
            print("❌ FFmpeg failed to create output. Returning original.")
            return input_path

    except Exception as e:
        print(f"❌ Normalization Failed: {e}")
        return input_path