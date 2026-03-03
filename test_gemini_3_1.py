import os
import google.generativeai as genai_v1
from google import genai as genai_v2
from dotenv import load_dotenv
import time

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def test_v1():
    print("\n--- Testing SDK v1 (google.generativeai) ---")
    try:
        genai_v1.configure(api_key=api_key)
        model = genai_v1.GenerativeModel('gemini-3.1-pro-preview')
        response = model.generate_content("Olá, você está funcionando?", request_options={'timeout': 30})
        print(f"SDK v1 Response: {response.text}")
    except Exception as e:
        print(f"SDK v1 Error: {e}")

def test_v2():
    print("\n--- Testing SDK v2 (google.genai) ---")
    try:
        client = genai_v2.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents="Olá, você está funcionando?"
        )
        print(f"SDK v2 Response: {response.text}")
    except Exception as e:
        print(f"SDK v2 Error: {e}")

if __name__ == "__main__":
    test_v1()
    time.sleep(2)
    test_v2()
