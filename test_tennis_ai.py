import os
from dotenv import load_dotenv
from google import genai  # <--- Notice the import change

# 1. Load the environment variables
load_dotenv()

# 2. Create the Client (The new way)
# This 'client' object will handle all your requests
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

prompt = """
You are a professional tennis coach. 
Explain the tactical difference between a 'kick serve' and a 'slice serve'.
When should I use each one during a match? 
Keep the answer concise (under 200 words).
"""

print(f"Sending prompt to AI using the NEW library...")
print("-" * 30)

try:
    # 3. Generate Content
    # We pass the model name directly in the function call now
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=prompt
    )
    
    # 4. Print the result
    print("AI RESPONSE:")
    print(response.text)
    
except Exception as e:
    print(f"An error occurred: {e}")