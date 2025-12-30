import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import time

st.set_page_config(page_title="FindIt - Cloud Demo", layout="wide")

st.title("🔍 FindIt - Cloud Version")

st.info("""
**Cloud Deployment Notice:**
Since this app is running on Streamlit Cloud, it cannot directly access your local network (LAN).
- **Live Feed**: Not available (cannot connect to your local ESP32).
- **Backend AI**: Requires a public backend URL (e.g., via ngrok).
""")

# Sidebar
st.sidebar.header("Cloud Configuration")
backend_url = st.sidebar.text_input("Public Backend URL (e.g., ngrok)", value="")

status = st.sidebar.empty()

if backend_url:
    try:
        response = requests.get(f"{backend_url}/")
        if response.status_code == 200:
            status.success("Backend Connected")
        else:
            status.error("Backend Error")
    except Exception as e:
        status.error(f"Connection Failed: {e}")
else:
    status.warning("Please enter a backend URL")

# Tabs
tab1, tab2 = st.tabs(["Upload & Analyze", "Live Feed (Demo)"])

with tab1:
    st.header("📷 Upload Image")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Preview", width=300)
        
        if st.button("Analyze with AI"):
            if not backend_url:
                st.error("Please configure a Backend URL in the sidebar first.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                status_text.text("Preparing upload...")
                progress_bar.progress(10)
                
                try:
                    uploaded_file.seek(0)
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    
                    status_text.text("Sending to backend...")
                    progress_bar.progress(40)
                    
                    res = requests.post(f"{backend_url}/upload", files=files, timeout=30)
                    
                    progress_bar.progress(80)
                    status_text.text("Processing AI response...")
                    
                    if res.status_code == 200:
                        data = res.json()
                        progress_bar.progress(100)
                        status_text.success("Complete!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.json(data['detected'])
                        with col2:
                            if "annotated_url" in data:
                                # Fix URL if relative
                                img_url = data['annotated_url']
                                if img_url.startswith("/"):
                                    img_url = f"{backend_url}{img_url}"
                                st.image(img_url, caption="AI Result", use_container_width=True)
                    else:
                        st.error(f"Error: {res.status_code}")
                except Exception as e:
                    st.error(f"Failed: {e}")

with tab2:
    st.header("Live Feed")
    if not backend_url:
        st.warning("Live feed requires a public backend URL tunnelling to your local ESP32.")
        st.image("https://placehold.co/640x480?text=No+Signal", caption="Placeholder Signal")
    else:
        # User needs to manually input ESP32 public URL if they exposed it, or use backend proxy
        st.write("To view the live feed, your backend must be able to reach the ESP32 IP.")
        camera_ip = st.text_input("ESP32 Local IP (if backend is on same network)", "192.168.31.57")
        
        if st.button("Start Stream"):
            proxy_url = f"{backend_url}/proxy_stream?url=http://{camera_ip}:81/stream&ai=true"
            st.image(proxy_url, use_container_width=True)
