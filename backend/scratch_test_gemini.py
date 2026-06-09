import os
import google.generativeai as genai

print("EMERGENT_LLM_KEY:", os.environ.get("EMERGENT_LLM_KEY"))
print("GEMINI_API_KEY:", os.environ.get("GEMINI_API_KEY"))

try:
    # Try configuring with the key in environment if present, or let it auto-configure
    genai.configure()
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Write a one-word greeting.")
    print("Gemini response:", response.text.strip())
except Exception as e:
    print("Gemini call failed:", e)
