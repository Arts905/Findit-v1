from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import shutil
import os
import uuid
import json
import requests
import cv2
import numpy as np

from database import init_db, get_db, Item
from ai_engine import AIEngine

app = FastAPI(title="FindIt API")

# Ensure images directory exists
IMAGES_DIR = "images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Initialize AI Engine
ai_engine = AIEngine()

# Load Aliases
# Use absolute path relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALIASES_FILE = os.path.join(BASE_DIR, "aliases.json")

aliases_map = {}
if os.path.exists(ALIASES_FILE):
    try:
        with open(ALIASES_FILE, "r", encoding="utf-8") as f:
            aliases_map = json.load(f)
    except Exception as e:
        print(f"Error loading aliases: {e}")

@app.get("/status/model")
def get_model_status():
    """
    Check if AI model is loaded and working
    """
    if not ai_engine.model:
        return {"status": "error", "message": "Model not loaded"}
    
    # Try a dummy inference on a black image
    try:
        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        ai_engine.process_frame(dummy_frame)
        return {"status": "ok", "message": "Model operational", "model_type": "YOLOv8-World"}
    except Exception as e:
        return {"status": "error", "message": f"Inference failed: {str(e)}"}

@app.on_event("startup")
def on_startup():
    init_db()

app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

@app.get("/proxy_stream")
def proxy_stream(url: str, ai: bool = True):
    """
    Real-time AI Stream Proxy.
    Reads MJPEG from ESP32, runs YOLO, and streams back annotated frames.
    """
    def iterfile():
        try:
            # Use requests to get the stream with a timeout to prevent blocking
            with requests.get(url, stream=True, timeout=5) as r:
                if r.status_code != 200:
                    print(f"Stream returned status code: {r.status_code}")
                    # Yield a placeholder or error frame?
                    return

                bytes_data = b''
                for chunk in r.iter_content(chunk_size=4096):
                    bytes_data += chunk
                    a = bytes_data.find(b'\xff\xd8') # JPEG Start
                    b = bytes_data.find(b'\xff\xd9') # JPEG End
                    
                    if a != -1 and b != -1:
                        jpg = bytes_data[a:b+2]
                        bytes_data = bytes_data[b+2:]
                        
                        if ai:
                            # Decode to opencv image
                            img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if img is not None:
                                # AI Process
                                img = ai_engine.process_frame(img)
                                # Re-encode
                                ret, buffer = cv2.imencode('.jpg', img)
                                if ret:
                                    frame_bytes = buffer.tobytes()
                                    yield (b'--frame\r\n'
                                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                        else:
                            # Just yield original bytes if no AI
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
                                   
        except Exception as e:
            print(f"Stream error: {e}")
            # Optional: yield an error image here so frontend sees something


    return StreamingResponse(iterfile(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/upload")
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Save the file
    file_ext = file.filename.split(".")[-1]
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{file_ext}"
    file_path = os.path.join(IMAGES_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Run AI Inference
    detected_objects, annotated_path = ai_engine.analyze_image(file_path)
    
    # 3. Save to DB
    saved_items = []
    if detected_objects:
        for obj in detected_objects:
            # We save the ANNOTATED image path to DB so user sees the boxes by default?
            # Or we save raw path but return annotated?
            # Let's save the raw path to DB (clean history), but return annotated for immediate view.
            # Actually, user wants to see "where is it" in history too. 
            # Let's update the DB to store annotated path? Or just logic to find it?
            # Simple approach: Save the annotated image path in DB.
            
            # Wait, if we save annotated path, we lose the clean image. 
            # Better: Save raw path. In query response, check if annotated exists.
            
            item = Item(
                name=obj["name"],
                location=obj["location_desc"], # Now using logical zones
                image_path=file_path,
                timestamp=datetime.now()
            )
            db.add(item)
            saved_items.append(obj)
    else:
        # If nothing detected, maybe save a generic "snapshot" record? 
        # For now, we only save detected items as per requirements.
        pass
        
    db.commit()
    
    return {
        "status": "success", 
        "filename": filename, 
        "detected": saved_items,
        "annotated_url": f"/images/{os.path.basename(annotated_path)}"
    }

@app.get("/query")
async def query_item(q: str, db: Session = Depends(get_db)):
    q_lower = q.lower().strip()
    
    # Check if query matches any alias value
    # Format: {"english_name": ["alias1", "alias2"]}
    target_names = [q_lower] # Default: search for input literally
    
    found_alias = False
    for eng_name, alias_list in aliases_map.items():
        if q_lower == eng_name or q_lower in alias_list:
            if not found_alias:
                target_names = [] # Clear default if we find a match
                found_alias = True
            target_names.append(eng_name)
            
    # If no alias found, maybe user entered part of an alias?
    if not found_alias:
        for eng_name, alias_list in aliases_map.items():
            for alias in alias_list:
                if q_lower in alias: # Partial match: "我的钱包" -> matches "钱包" -> "wallet"
                    if not found_alias:
                        target_names = []
                        found_alias = True
                    if eng_name not in target_names:
                        target_names.append(eng_name)

    # Perform Query
    # We construct a query that looks for ANY of the target names
    # AND also keep the original behavior of partial match on the stored name (which is English)
    
    # SQLAlchemy IN clause
    items = db.query(Item).filter(Item.name.in_(target_names)).order_by(Item.timestamp.desc()).all()
    
    # Fallback: if exact alias match failed, try like search on original input (in case it was English)
    if not items and not found_alias:
         items = db.query(Item).filter(Item.name.contains(q_lower)).order_by(Item.timestamp.desc()).all()
    
    if not items:
        return {"message": f"未找到物品: {q}", "items": []}
    
    results = []
    for item in items:
        # Try to find Chinese name for display if available
        display_name = item.name
        if item.name in aliases_map:
             display_name = f"{aliases_map[item.name][0]} ({item.name})"

        # Determine image URL
        # Check if annotated version exists
        base_name, ext = os.path.splitext(item.image_path)
        annotated_path = f"{base_name}_annotated{ext}"
        
        if os.path.exists(annotated_path):
            img_url = f"/images/{os.path.basename(annotated_path)}"
        else:
            img_url = f"/images/{os.path.basename(item.image_path)}"

        results.append({
            "name": display_name,
            "location": item.location,
            "time": item.timestamp.isoformat(),
            "image_url": img_url
        })
        
    return {"items": results}

@app.get("/")
def read_root():
    return {"message": "FindIt Backend is running"}

if __name__ == "__main__":
    import uvicorn
    # Listen on all interfaces so ESP32 can connect
    uvicorn.run(app, host="0.0.0.0", port=8001)
