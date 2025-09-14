
import requests
import json
import os

# --- Configuration ---
API_URL = "http://localhost:41184"
API_TOKEN = "a4ced1ba65c868ca33892ae2421736a096e4e52d3b54f3712c08bae9c2843115a0b08a0f0feaf915ef1d2c9346beb937f0ef5d72597c08137766f1fbae41eccf"
NOTE_IDS = ["c26894b536b94570a78add186e5ddf67", "00369358e2b94b9db249ac7061dcba8d"]
# To see all available data, we request all common fields.
FIELDS = "id,parent_id,title,body,created_time,updated_time,source_url,author,is_todo,todo_due,todo_completed,user_created_time,user_updated_time"

def fetch_note(note_id):
    """Fetches a single note from the Joplin API."""
    url = f"{API_URL}/notes/{note_id}"
    params = {
        "token": API_TOKEN,
        "fields": FIELDS
    }
    try:
        response = requests.get(url, params=params)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Connection Error", "message": "Could not connect to Joplin API. Is Joplin running and is the Web Clipper service enabled at http://localhost:41184?"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def main():
    """Fetches the specified notes and prints their content."""
    print("--- Testing Joplin API ---")
    all_notes_data = []
    for note_id in NOTE_IDS:
        print(f"\n--- Fetching Note ID: {note_id} ---")
        note_data = fetch_note(note_id)
        # Pretty print the JSON response
        print(json.dumps(note_data, indent=2, ensure_ascii=False))
        all_notes_data.append(note_data)
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    main()
