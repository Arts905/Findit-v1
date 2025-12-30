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
tab1, tab2, tab3 = st.tabs(["Upload & Analyze", "Live Feed (Demo)", "Find My Stuff"])

def get_image_bytes(url):
    """
    Fetch image from backend (Ngrok) with custom headers to bypass warning page.
    """
    try:
        # Ngrok free tier adds a warning page for browsers.
        # We must add this header to tell Ngrok it's a programmatic request.
        headers = {"ngrok-skip-browser-warning": "true"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.content
        else:
            return None
    except Exception as e:
        st.error(f"Image load failed: {e}")
        return None

with tab1:
    st.header("📷 Upload Image")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Preview", width=300)
        
        if st.button("Analyze with AI"):
            if not backend_url:
                st.error("Please configure a Backend URL in the sidebar first.")
            else:
                # Normalize backend URL
                backend_url = backend_url.rstrip('/')
                
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
                                
                                # Use proxy fetch to bypass ngrok warning
                                img_bytes = get_image_bytes(img_url)
                                if img_bytes:
                                    st.image(img_bytes, caption="AI Result", use_container_width=True)
                                else:
                                    st.error("Could not load result image.")
                            else:
                                st.warning("No annotated image returned.")
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
        # Normalize backend URL
        backend_url = backend_url.rstrip('/')
        
        # User needs to manually input ESP32 public URL if they exposed it, or use backend proxy
        st.write("To view the live feed, your backend must be able to reach the ESP32 IP.")
        camera_ip = st.text_input("ESP32 Local IP (if backend is on same network)", "192.168.31.57")
        
        if st.button("Start Stream"):
            proxy_url = f"{backend_url}/proxy_stream?url=http://{camera_ip}:81/stream&ai=true"
            st.image(proxy_url, use_container_width=True)

with tab3:
    st.header("🔍 Find My Stuff")
    st.write("Search for items you've previously uploaded/detected.")
    
    if not backend_url:
        st.error("Please configure a Backend URL in the sidebar first.")
    else:
        backend_url = backend_url.rstrip('/')
        query = st.text_input("What are you looking for? (e.g., keys, wallet)", "")
        
        if st.button("Search") or query:
            if query:
                try:
                    with st.spinner("Searching..."):
                        res = requests.get(f"{backend_url}/query", params={"q": query}, timeout=10)
                        
                        if res.status_code == 200:
                            results = res.json()
                            if "items" in results and results["items"]:
                                # Limit results to 20 to prevent overload
                                items = results["items"][:20]
                                st.success(f"Found {len(results['items'])} items matching '{query}' (Showing latest {len(items)})")
                                
                                for item in items:
                                    with st.container():
                                        c1, c2 = st.columns([1, 2])
                                        with c1:
                                            # Construct full image URL
                                            img_url = item.get("image_url", "")
                                            if img_url.startswith("/"):
                                                img_url = f"{backend_url}{img_url}"
                                            
                                            # Use proxy fetch
                                            img_bytes = get_image_bytes(img_url)
                                            if img_bytes:
                                                st.image(img_bytes, use_container_width=True)
                                            else:
                                                st.warning("Image unavailable")
                                        with c2:
                                            st.subheader(item["name"])
                                            st.write(f"**Location:** {item['location']}")
                                            st.write(f"**Time:** {item['time']}")
                                        st.divider()
                            else:
                                st.info(f"No items found matching '{query}'.")
                        else:
                            st.error(f"Search failed: {res.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
            else:
                st.warning("Please enter a search term.")

with tab4:
    st.header("🏠 3D Room Map")
    st.info("Upload your room's 3D model (.glb) to visualize the environment. You can use apps like Polycam or LiDAR scanners to generate this.")
    
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
        # Optional: Demo placeholder
        if st.checkbox("Show Demo Model"):
             # Use a public sample model (Astronaut) from Google's model-viewer examples
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
