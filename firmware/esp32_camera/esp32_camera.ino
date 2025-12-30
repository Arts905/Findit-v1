#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"
#include "secrets.h"

// ===================
// Select Camera Model
// ===================
#define CAMERA_MODEL_AI_THINKER // Has PSRAM

#include "camera_pins.h"

// Timer for periodic upload
unsigned long lastCaptureTime = 0;
const int captureInterval = 30000; // 30 seconds

// Web Server for streaming
WiFiServer streamServer(81);

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  // 1. Initialize Camera FIRST (Before WiFi)
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  
  // Try 10MHz first
  config.xclk_freq_hz = 10000000; 
  config.frame_size = FRAMESIZE_QVGA; 
  config.pixel_format = PIXFORMAT_JPEG; 
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_DRAM; // Use DRAM for safety
  config.jpeg_quality = 12; 
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  
  if (err != ESP_OK) {
    Serial.printf("Init failed (0x%x). Retrying with 5MHz...\n", err);
    // Retry with lower frequency
    config.xclk_freq_hz = 5000000; 
    err = esp_camera_init(&config);
    if (err != ESP_OK) {
       Serial.printf("Retry failed. Halting.\n");
       while(true) delay(100);
    }
  }

  Serial.println("Camera Init SUCCESS!");

  // OV3660 Sensor Settings
  sensor_t * s = esp_camera_sensor_get();
  if (s->id.PID == OV3660_PID) {
    Serial.println("OV3660 Detected");
    s->set_brightness(s, 1); 
    s->set_saturation(s, -2);
  }

  // 2. Initialize WiFi AFTER Camera is stable
  WiFi.begin(ssid, password);
  // WiFi.setSleep(false); // Disable WiFi sleep to ensure stability
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("Stream Ready! Go to: http://");
  Serial.print(WiFi.localIP());
  Serial.println(":81/stream");
  
  streamServer.begin();
}

void loop() {
  // Handle Stream Clients
  WiFiClient client = streamServer.available();
  if (client) {
    // Serial.println("New Stream Client."); // Reduce logging
    String currentLine = "";
    if (client.connected()) {
      client.println("HTTP/1.1 200 OK");
      client.println("Content-Type: multipart/x-mixed-replace; boundary=frame");
      client.println();
      
      while (client.connected()) {
        camera_fb_t * fb = esp_camera_fb_get();
        if (!fb) {
          // Serial.println("Camera capture failed");
          // Re-init camera if capture fails continuously?
          break;
        }
        
        client.println("--frame");
        client.println("Content-Type: image/jpeg");
        client.println("Content-Length: " + String(fb->len));
        client.println();
        client.write(fb->buf, fb->len);
        client.println();
        
        esp_camera_fb_return(fb);
        delay(100); 
      }
    }
    client.stop();
    // Serial.println("Client Disconnected.");
  }

  // Periodic Upload Task
  if (millis() - lastCaptureTime > captureInterval) {
    takePictureAndUpload();
    lastCaptureTime = millis();
  }
  
  delay(10);
}

void takePictureAndUpload() {
  camera_fb_t * fb = NULL;
  
  // Take Picture with Camera
  fb = esp_camera_fb_get();  
  if(!fb) {
    Serial.println("Capture failed during upload task");
    return;
  }
  
  Serial.printf("Picture taken! Size: %d bytes\n", fb->len);
  
  // Upload to Server
  if(WiFi.status() == WL_CONNECTED) {
    String boundary = "------------------------esp32camera";
    String contentType = "multipart/form-data; boundary=" + boundary;
    
    // Parse URL for host and port
    String urlStr = String(server_url);
    int portIndex = urlStr.indexOf(":", 7);
    int pathIndex = urlStr.indexOf("/", 7);
    
    String host = urlStr.substring(7, portIndex);
    int port = urlStr.substring(portIndex + 1, pathIndex).toInt();
    String path = urlStr.substring(pathIndex);
    
    WiFiClient client;
    if (client.connect(host.c_str(), port)) {
      Serial.println("Connected to server");
      
      String head = "--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
      String tail = "\r\n--" + boundary + "--\r\n";
      
      uint32_t totalLen = fb->len + head.length() + tail.length();
      
      client.println("POST " + path + " HTTP/1.1");
      client.println("Host: " + host);
      client.println("Content-Type: " + contentType);
      client.println("Content-Length: " + String(totalLen));
      client.println();
      
      client.print(head);
      
      // Send image data in chunks
      uint8_t *fbBuf = fb->buf;
      size_t fbLen = fb->len;
      size_t chunkSize = 1024;
      
      for (size_t i = 0; i < fbLen; i += chunkSize) {
        size_t toSend = (fbLen - i < chunkSize) ? (fbLen - i) : chunkSize;
        client.write(fbBuf + i, toSend);
      }
      
      client.print(tail);
      
      // Read response
      while (client.connected()) {
        String line = client.readStringUntil('\n');
        if (line == "\r") {
          break;
        }
      }
      
      client.stop();
      Serial.println("Upload done.");
    } else {
      Serial.println("Connection failed");
    }
  }
  
  esp_camera_fb_return(fb); 
}
