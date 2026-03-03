import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def test_v2():
    print("\n--- Testing SDK v2 (google.genai) ---")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents="Olá, você está funcionando?"
        )
        if hasattr(response, 'text'):
            print(f"SDK v2 Response: {response.text}")
        else:
            print("SDK v2 Response has no text attribute.")
    except Exception as e:
        print(f"SDK v2 Error: {e}")

if __name__ == "__main__":
    test_v2()
