# Software Architecture & Proof of Concept (PoC) Plan

## 1. Context & Overall Software Plan
The final production version of this smart helmet module will require highly optimized C/C++ firmware running on a low-power microcontroller (MCU), tightly coupled with a companion iOS/Android mobile app via Bluetooth Low Energy (BLE). 

However, to validate the core logic—specifically the asymmetric sensor fusion (radar triggering the camera) and the crash detection thresholds—we must first build a "Frankenstein" Proof of Concept (PoC). 

**This document outlines the software architecture for the Phase 1 PoC, which will be built on a Raspberry Pi (e.g., Pi Zero 2 W) using Python.** Python allows for rapid iteration of the logic before committing to complex, low-level MCU firmware.

---

## 2. PoC Hardware & OS Stack
*   **Compute:** Raspberry Pi Zero 2 W
*   **Camera:** Raspberry Pi Camera Module (connected via CSI ribbon cable). *Note: The CSI connection is critical here as it bypasses the USB bus, utilizing the Pi's GPU for image capture and saving vital CPU resources for AI processing.*
*   **Operating System:** Raspberry Pi OS Lite (headless, no desktop environment to save resources)
*   **Primary Language:** Python 3.9+
*   **Key Libraries:** OpenCV or Picamera2 (for camera), TensorFlow Lite (for coarse AI classification), smbus/CircuitPython (for I2C/IMU communication), PySerial (for UART/Radar communication).

---

## 3. Core Software Modules (Python Scripts)
The PoC software will be broken down into discrete modules managed by a central controller script.

### A. `radar_watchman.py`
*   **Function:** Continuously reads serial data via UART from the mmWave radar sensor.
*   **Logic:** Parses the data stream for distance and velocity metrics. 
*   **Action:** If an object is detected within a specific distance (e.g., < 50 meters) AND the closing velocity exceeds the danger threshold (e.g., > 15 mph), it flips a boolean trigger flag (`THREAT_DETECTED = True`).

### B. `camera_classifier.py`
*   **Function:** Handles the CSI Camera Module and lightweight AI classification.
*   **Logic:** Remains in a dormant/wait state to simulate the "deep sleep" of the final product. 
*   **Action:** When `THREAT_DETECTED` is flagged by the radar, this script wakes up, grabs the next 3-5 frames from the CSI camera, and passes them through a pre-trained TensorFlow Lite MobileNet model. 
*   **Output:** Returns a simple string classification: "Car", "Truck", "Motorcycle", or "Unknown".

### C. `crash_detect.py`
*   **Function:** Monitors the 6-axis IMU (Accelerometer/Gyroscope) via I2C.
*   **Logic:** Continuously calculates the magnitude of the G-force vector. 
*   **Action:** If a sudden deceleration spike exceeds the established "crash threshold" (e.g., > 6Gs) followed by zero movement, it triggers the `SOS_PROTOCOL` flag.

### D. `alert_manager.py`
*   **Function:** Handles audio feedback and simulated Bluetooth triggers.
*   **Logic (Collision):** Takes the output from `camera_classifier.py` and triggers a specific text-to-speech audio file over the Pi's Bluetooth connection to a standard headset (e.g., "Fast truck approaching left").
*   **Logic (Crash):** When `SOS_PROTOCOL` is triggered, it initiates a 15-second audio countdown ("Crash detected, calling 911 in 15 seconds"). If not canceled, it sends a mock API webhook to simulate a phone sending an emergency text.

### E. `main_controller.py`
*   **Function:** The orchestrator. Uses Python `multiprocessing` or `asyncio` to run these modules concurrently, ensuring the radar watchman never stops listening while the camera processes images.

---

## 4. Phase 1 Milestones for the PoC
1.  **Sensor Read/Write:** Successfully pull raw data from the mmWave radar and IMU into terminal outputs.
2.  **The Trigger Handshake:** Prove that `radar_watchman.py` can successfully trigger the hardware interrupt to wake up the camera script with less than 200ms of latency.
3.  **Threshold Tuning:** Ride a bicycle in a safe, controlled environment (like an empty parking lot with a friend driving a car) to establish the exact G-force limits for a crash and the velocity thresholds for a collision warning.