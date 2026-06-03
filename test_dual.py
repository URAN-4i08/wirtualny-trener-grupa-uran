import requests
import time

print("Setting dual cam source...")
r1 = requests.post("http://127.0.0.1:8000/api/source/camera-dual?camera_index_a=1&camera_index_b=0")
print(r1.status_code, r1.text)

print("Fetching video feed dual...")
try:
    r2 = requests.get("http://127.0.0.1:8000/video_feed_dual", stream=True, timeout=5)
    print("Status:", r2.status_code)
    for line in r2.iter_lines():
        if line:
            print("Received bytes:", len(line), line[:50])
            break
except Exception as e:
    print("Error:", e)
