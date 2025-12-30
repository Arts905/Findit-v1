import requests
import os

# Use localhost to test server status
BASE_URL = "http://192.168.31.13:8000"
IMAGE_PATH = "bus.jpg"

def test_upload():
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: {IMAGE_PATH} not found.")
        return

    print(f"Uploading {IMAGE_PATH} to {BASE_URL}/upload ...")
    try:
        with open(IMAGE_PATH, "rb") as f:
            files = {"file": f}
            res = requests.post(f"{BASE_URL}/upload", files=files, timeout=5)
        
        if res.status_code == 200:
            print("Upload Success!")
            print("Response:", res.json())
        else:
            print(f"Upload Failed: {res.status_code}")
            print(res.text)
    except Exception as e:
        print(f"Connection Error: {e}")
        print("Please check if server is running.")

if __name__ == "__main__":
    test_upload()
