from ultralytics import YOLO
import os
import json

class AIEngine:
    def __init__(self, model_path="yolov8s-world.pt", zones_path=None):
        # Resolve zones.json path relative to this file if not provided
        if zones_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            zones_path = os.path.join(base_dir, "zones.json")

        # Load YOLO model
        # Try to load YOLO-World first for open vocabulary, fallback to standard YOLOv8n
        self.model = None
        
        try:
            print("Attempting to load YOLOv8s-Worldv2 model (Open Vocabulary)...")
            self.model = YOLO("yolov8s-worldv2.pt")
            
            # Define custom classes to include things NOT in COCO
            custom_classes = [
                "person", "wallet", "keys", "key", "bunch of keys", 
                "cell phone", "smartphone", "laptop", "computer",
                "computer mouse", "mouse", "keyboard", "bottle", "water bottle", 
                "cup", "mug", "glasses", "sunglasses", 
                "remote control", "remote", "book", "backpack", "bag", "handbag", 
                "headphones", "headset", "earphones", "watch"
            ]
            
            # Only call set_classes if the method exists (it should for World models)
            if hasattr(self.model, 'set_classes'):
                self.model.set_classes(custom_classes)
                print(f"YOLO-World loaded with custom classes: {custom_classes}")
            else:
                print("Loaded model does not support set_classes, using default classes.")
                
        except Exception as e:
            print(f"Error loading YOLO-World model: {e}")
            print("Falling back to standard YOLOv8n...")
            try:
                self.model = YOLO("yolov8n.pt")
                print("YOLOv8n loaded as fallback.")
            except Exception as e2:
                print(f"Critical error loading fallback model: {e2}")
                self.model = None

        self.zones = self.load_zones(zones_path)

    def load_zones(self, zones_path):
        if os.path.exists(zones_path):
            try:
                with open(zones_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading zones: {e}")
                return {}
        return {}

    def get_location_description(self, x_center_norm, y_center_norm):
        # Default fallback
        location_desc = "未知区域"
        
        # Simple horizontal fallback if no zones match
        if x_center_norm < 0.33:
            location_desc = "左侧"
        elif x_center_norm > 0.66:
            location_desc = "右侧"
        else:
            location_desc = "中间"

        # Check against defined zones
        # Prioritize checking smaller zones or specific order if needed
        # Here we just check all and take the first match or last match
        for zone_name, zone_data in self.zones.items():
            if (zone_data['x_min'] <= x_center_norm <= zone_data['x_max'] and
                zone_data['y_min'] <= y_center_norm <= zone_data['y_max']):
                return zone_data['description']
        
        return location_desc

    def process_frame(self, frame):
        if not self.model:
            return frame
            
        try:
            results = self.model(frame)
            annotated_frame = results[0].plot()
            return annotated_frame
        except Exception as e:
            print(f"Inference error: {e}")
            return frame

    def analyze_image(self, image_path):
        if not self.model:
            return [], image_path
            
        try:
            results = self.model(image_path)
            detected_items = []
            
            # We process the first result (since we infer one image)
            result = results[0]
            
            # Save annotated image
            annotated_frame = result.plot()
            # Save to the same directory but with a suffix
            # e.g. images/xxx.jpg -> images/xxx_annotated.jpg
            base_name, ext = os.path.splitext(image_path)
            annotated_path = f"{base_name}_annotated{ext}"
            
            # Ultralytics plot() returns a numpy array (BGR), we need to save it.
            # We can use PIL or cv2. Since we have Pillow installed:
            from PIL import Image
            import numpy as np
            
            # Convert BGR (OpenCV format) to RGB
            im_rgb = annotated_frame[..., ::-1] 
            im = Image.fromarray(im_rgb)
            im.save(annotated_path)
    
            boxes = result.boxes
            img_width = result.orig_shape[1]
            img_height = result.orig_shape[0]
    
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                name = self.model.names[cls]
                
                # Calculate normalized center
                x1, y1, x2, y2 = box.xyxy[0]
                x_center = (x1 + x2) / 2
                y_center = (y1 + y2) / 2
                
                x_center_norm = float(x_center) / img_width
                y_center_norm = float(y_center) / img_height
                
                location_desc = self.get_location_description(x_center_norm, y_center_norm)
    
                if conf > 0.15: # Lowered Confidence threshold for Open Vocabulary
                    detected_items.append({
                        "name": name,
                        "confidence": conf,
                        "location_desc": location_desc,
                        "bbox": box.xyxy[0].tolist(),
                        "annotated_path": annotated_path # Return this so API knows
                    })
                        
            return detected_items, annotated_path
        except Exception as e:
            print(f"Analysis error: {e}")
            return [], image_path
