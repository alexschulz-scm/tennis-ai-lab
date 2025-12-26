import os
import shutil
import pathlib

print("🧹 STARTING CLEANUP...")

# 1. Walk through all directories
current_dir = pathlib.Path(__file__).parent
count = 0

for root, dirs, files in os.walk(current_dir):
    for d in dirs:
        if d == "__pycache__":
            path = os.path.join(root, d)
            print(f"   Deleting: {path}")
            try:
                shutil.rmtree(path)
                count += 1
            except Exception as e:
                print(f"   Error deleting {path}: {e}")

print(f"✅ CLEANUP COMPLETE. Removed {count} cache folders.")
print("👉 Now run: streamlit run app.py")