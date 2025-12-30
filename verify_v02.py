import requests
import time
import os

BASE_URL = "http://localhost:8000"

def wait_for_server():
    print("Waiting for server...")
    for i in range(30):
        try:
            requests.get(BASE_URL)
            print("Server is up!")
            return True
        except Exception as e:
            if i % 5 == 0:
                print(f"Waiting... ({e})")
            time.sleep(1)
    return False

def test_chinese_alias():
    # We need an image first. 
    # Let's download a sample image (bus.jpg)
    img_url = "https://ultralytics.com/images/bus.jpg"
    print(f"Downloading {img_url}...")
    try:
        r = requests.get(img_url)
        with open("bus.jpg", "wb") as f:
            f.write(r.content)
    except Exception as e:
        print(f"Failed to download image: {e}")
        return

    # Upload image
    print("Uploading image...")
    with open("bus.jpg", "rb") as f:
        files = {"file": f}
        res = requests.post(f"{BASE_URL}/upload", files=files)
    
    print("Upload response:", res.json())
    
    # Query for "公交车" (alias for bus)
    print("Querying for '公交车'...")
    res = requests.get(f"{BASE_URL}/query", params={"q": "公交车"})
    data = res.json()
    print("Query result for '公交车':", data)
    
    # Check if we found it
    if "items" in data and len(data["items"]) > 0:
        item = data["items"][0]
        print(f"[SUCCESS] Found: {item['name']} at {item['location']}")
    else:
        print("[FAILED] Failed to find item using alias '公交车'")

    # Query for "人" (alias for person)
    print("Querying for '人'...")
    res = requests.get(f"{BASE_URL}/query", params={"q": "人"})
    data = res.json()
    if "items" in data and len(data["items"]) > 0:
        item = data["items"][0]
        print(f"[SUCCESS] Found: {item['name']} at {item['location']}")
    else:
        print("[FAILED] Failed to find item using alias '人'")

if __name__ == "__main__":
    if wait_for_server():
        test_chinese_alias()
    else:
        print("Server failed to start.")
