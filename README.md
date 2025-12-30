# FindIt - Intelligent Home Item Finder

## Overview
FindIt is a smart home assistant that helps you locate items using visual AI. It consists of an ESP32-S3 camera that captures images, a backend server that processes them with YOLOv8, and a Web UI to search for items.

## v0.2 New Features
- **Chinese Alias Support**: You can now search for items using Chinese names (e.g., "钱包", "钥匙").
- **Logical Zone Mapping**: Item locations are now described by zones (e.g., "Sofa Area", "Coffee Table") instead of just coordinates.

## Project Structure
- `backend/`: FastAPI server + YOLOv8 AI Engine + SQLite Database.
  - `aliases.json`: Mapping of English COCO classes to Chinese aliases.
  - `zones.json`: Configuration for logical zones in the room.
- `firmware/`: ESP32-S3 Arduino code.
- `frontend/`: Streamlit Web Interface.

## Prerequisites
- Python 3.8+
- Arduino IDE (for flashing ESP32)
- ESP32-S3 Board + OV2640 Camera

## Setup Instructions

### 1. Backend Setup
1. Navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Customize `zones.json` to match your room layout.
4. Run the server:
   ```bash
   python main.py
   ```
   Server will start at `http://0.0.0.0:8000`.

### 2. Firmware Setup
1. Open `firmware/esp32_camera/esp32_camera.ino` in Arduino IDE.
2. Open `firmware/esp32_camera/secrets.h` and update:
   - `ssid`: Your WiFi Name.
   - `password`: Your WiFi Password.
   - `server_url`: Your PC's IP address (e.g., `http://192.168.1.5:8000/upload`).
3. Select Board: `ESP32S3 Dev Module` (or your specific board).
4. Enable PSRAM: "OPI PSRAM" (usually required for UXGA).
5. Flash the board.

### 3. Frontend Setup
1. Navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the UI:
   ```bash
   streamlit run streamlit_app.py
   ```
4. Open browser at `http://localhost:8501`.

## Usage
1. The camera will automatically upload an image every 30 seconds.
2. The backend analyzes the image using YOLOv8 and determines the logical zone (e.g., "Sofa Area").
3. Use the Frontend to ask "我的钱包在哪?" or "keys".
4. See the result with the zone description and the image.

## Customization
- **Aliases**: Edit `backend/aliases.json` to add more Chinese nicknames for items.
- **Zones**: Edit `backend/zones.json` to define coordinates (0.0-1.0) for different areas in your camera's view.

## Troubleshooting
- **Backend Error**: Ensure you have installed `ultralytics`. The first run will download the `yolov8n.pt` model automatically.
- **Camera Upload Failed**: Check the Serial Monitor in Arduino IDE. Ensure the ESP32 is on the same WiFi as your PC. Check if `server_url` IP is correct.
