import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import socket
import streamlit.components.v1 as components
import base64

# Function to get local IP address
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to an external server (doesn't actually establish a connection)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

# Backend URL
# Use dynamic IP to allow mobile access
LOCAL_IP = get_local_ip()
BACKEND_URL = f"http://{LOCAL_IP}:8001"

st.set_page_config(page_title="FindIt - Local (v1.1)", layout="wide")

st.title(f"🔍 FindIt - Local Version ({LOCAL_IP})")

# Sidebar
st.sidebar.header("Control Panel")
status = st.sidebar.empty()

try:
    response = requests.get(f"{BACKEND_URL}/")
    if response.status_code == 200:
        status.success("Backend Connected")
    else:
        status.error("Backend Error")
except Exception as e:
    status.error(f"Backend Offline: {e}")

# Helper to fetch images
def get_image_bytes(url):
    try:
        # For local, we can just fetch directly, but using this helper for consistency
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.content
        return None
    except:
        return None

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Search", "Live Feed / History", "Simulator (Upload)", "3D Room Map"])

with tab3:
    st.header("📷 Camera Simulator")
    st.write("No ESP32 camera? No problem! Upload an image here to simulate a camera capture.")
    
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        # Show preview
        st.image(uploaded_file, caption="Preview", width=300)
        
        if st.button("Upload to FindIt Backend"):
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Preparing upload...")
            progress_bar.progress(10)
            
            with st.spinner("Uploading and Analyzing..."):
                try:
                    # We need to send a proper filename
                    # Ensure file pointer is at start
                    uploaded_file.seek(0)
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    
                    status_text.text("Sending data to backend...")
                    progress_bar.progress(40)
                    
                    # Increase timeout for mobile networks/large images
                    res = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=30)
                    
                    progress_bar.progress(80)
                    status_text.text("Processing response...")
                    
                    if res.status_code == 200:
                        data = res.json()
                        progress_bar.progress(100)
                        status_text.success("Complete!")
                        st.success(f"Upload Successful! Saved as {data['filename']}")
                        st.json(data['detected'])
                        
                        if "annotated_url" in data:
                             st.subheader("👁️ AI Vision Analysis")
                             annotated_img_url = f"{BACKEND_URL}{data['annotated_url']}"
                             st.image(annotated_img_url, caption="Annotated Result", use_container_width=True)
                    else:
                        st.error(f"Upload failed: {res.status_code}")
                        st.write(res.text)
                except Exception as e:
                    st.error(f"Error: {e}")

with tab1:
    st.header("Ask FindIt")
    query = st.text_input("What are you looking for?", placeholder="e.g., wallet, keys, remote")
    
    if st.button("Find"):
        if query:
            try:
                res = requests.get(f"{BACKEND_URL}/query", params={"q": query})
                data = res.json()
                
                if "items" in data and data["items"]:
                    st.success(f"Found {len(data['items'])} occurrence(s) of '{query}'")
                    
                    for item in data["items"]:
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            # Construct full image URL
                            img_url = f"{BACKEND_URL}{item['image_url']}"
                            st.image(img_url, caption=item['time'], use_container_width=True)
                        with col2:
                            st.subheader(f"📍 {item['location']}")
                            st.write(f"**Detected Object:** {item['name']}")
                            st.write(f"**Time:** {item['time']}")
                            
                else:
                    st.warning("Item not found in recent history.")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")
        else:
             st.info("Please enter an item name.")

with tab2:
    st.header("Live Feed")
    
    # Sidebar Configuration
    camera_ip = st.sidebar.text_input("ESP32 Camera IP", value="192.168.31.57")
    ai_enabled = st.sidebar.checkbox("Enable Real-time AI Overlay", value=True)
    
    st.sidebar.markdown("---")
    st.sidebar.header("System Health")
    
    if st.sidebar.button("Check AI Model"):
        try:
            res = requests.get(f"{BACKEND_URL}/status/model", timeout=5)
            if res.status_code == 200:
                status_data = res.json()
                if status_data["status"] == "ok":
                    st.sidebar.success(f"✅ AI Model: {status_data['message']}")
                else:
                    st.sidebar.error(f"❌ AI Model: {status_data['message']}")
            else:
                st.sidebar.error(f"❌ Backend Error: {res.status_code}")
        except Exception as e:
            st.sidebar.error(f"❌ Connection Failed: {e}")
    
    # Use Backend Proxy to avoid Mixed Content (HTTP vs HTTPS/Localhost security)
    # The frontend talks to LOCAL_IP:8000, and LOCAL_IP:8000 talks to ESP32
    esp_stream_url = f"http://{camera_ip}:81/stream"
    proxy_url = f"http://{LOCAL_IP}:8001/proxy_stream?url={esp_stream_url}&ai={str(ai_enabled).lower()}"
    
    # Main Video Container - Make it full width and prominent
    st.image(proxy_url, use_container_width=True)
    
    st.markdown("---")
    st.header("Recent Detections")
    # In a real app, we'd have a specific endpoint for recent items, 
    # but for now we can query for everything or just show a placeholder
    # Let's add a "Recent" endpoint to backend effectively by querying for common items
    
    if st.button("Refresh Recent"):
        # For demo, just query common items
        common_items = ["person", "cup", "bottle", "keyboard", "mouse", "cell phone"]
        found_any = False
        
        for item_name in common_items:
            try:
                res = requests.get(f"{BACKEND_URL}/query", params={"q": item_name})
                data = res.json()
                if "items" in data and data["items"]:
                    found_any = True
                    st.subheader(f"Recent '{item_name}'")
                    # Show top 1
                    item = data["items"][0]
                    
                    img_url = f"{BACKEND_URL}{item['image_url']}"
                    # Use helper
                    img_bytes = get_image_bytes(img_url)
                    if img_bytes:
                        st.image(img_bytes, width=300)
                    else:
                        st.warning("Image unavailable")
                        
                    st.write(f"Location: {item['location']} at {item['time']}")
                    st.markdown("---")
            except:
                pass
        
        if not found_any:
            st.info("No common items detected recently.")

with tab4:
    st.header("🏠 3D Room Map")
    st.info("Upload your room's 3D model (.glb) to visualize the environment.")
    
    uploaded_model = st.file_uploader("Upload 3D Model (.glb)", type=["glb"])
    
    if uploaded_model:
        # Encode file to base64 to embed in HTML
        bytes_data = uploaded_model.getvalue()
        b64 = base64.b64encode(bytes_data).decode()
        mime = "model/gltf-binary"
        
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
            <style>
                body {{ margin: 0; }}
                model-viewer {{
                    width: 100%;
                    height: 600px;
                    background-color: #f0f2f6;
                    --poster-color: #f0f2f6;
                }}
            </style>
        </head>
        <body>
            <model-viewer 
                src="data:{mime};base64,{b64}" 
                camera-controls 
                auto-rotate
                shadow-intensity="1"
                ar>
                <div slot="progress-bar"></div>
            </model-viewer>
        </body>
        </html>
        """
        components.html(html_code, height=600)
    else:
        st.write("No model uploaded yet.")
        if st.checkbox("Show Demo Model"):
             demo_html = """
             <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
             <model-viewer 
                 src="https://modelviewer.dev/shared-assets/models/Astronaut.glb" 
                 alt="A 3D model of an astronaut"
                 auto-rotate 
                 camera-controls
                 style="width: 100%; height: 500px; background-color: #f0f2f6;">
             </model-viewer>
             """
             components.html(demo_html, height=500)
