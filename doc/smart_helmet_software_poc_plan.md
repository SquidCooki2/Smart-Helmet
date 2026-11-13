# Software Architecture & Proof of Concept (PoC) Plan

## 1. The "Radar-Triggered Snapshot" Architecture

This software PoC relies on an ESP32-CAM (or ESP32-S3) microcontroller. The ESP32 is responsible for three simultaneous tasks: writing a continuous video loop to a MicroSD card, listening to the mmWave radar, and sending a single JPEG to the phone when triggered. 

The smartphone companion app acts as the "brain," running a local machine-learning model to classify the image and trigger the audio alert.

## 2. Hardware Required for PoC
*   **Microcontroller:** ESP32-S3 with PSRAM and an OV2640 camera module (handles SD card writing and Bluetooth 5.0).
*   **Radar Sensor:** LD2410 or similar low-power 24GHz mmWave radar module.
*   **Storage:** MicroSD card (for the continuous dashcam loop).
*   **Receiver:** A smartphone (iOS or Android) running a basic test app.

## 3. The Core Software Loop (ESP32 Firmware)

The C++/Arduino firmware on the ESP32 will run in a continuous loop utilizing RTOS (Real-Time Operating System) tasks to prevent the SD card recording from blocking the Bluetooth transmission.

**Task 1: The Dashcam Loop (Core 0)**
*   Continuously captures frames from the camera buffer.
*   Writes an MJPEG stream directly to the MicroSD card in 3-minute chunks.
*   Overwrites the oldest chunk when the SD card is full.

**Task 2: The Radar Watchdog (Core 1)**
*   Continuously reads the serial output from the mmWave radar chip.
*   Filters out objects moving *away* from the bike or matching the bike's speed.
*   **The Trigger:** When a *new* object enters the zone closing at a dangerous speed (e.g., +15 mph differential), it triggers Task 3.

**Task 3: The BLE Snapshot Handoff (Core 1)**
*   Upon radar trigger, the ESP32 pulls the *very next frame* from the camera buffer.
*   Compresses that single frame to a low-resolution JPEG (e.g., 320x240, ~15KB).
*   Chops the JPEG into 512-byte packets (the BLE Maximum Transmission Unit).
*   Fires those packets over Bluetooth to the connected smartphone.

## 4. Bluetooth (BLE) GATT Architecture

To make the helmet talk to the phone, you will need to set up a GATT (Generic Attribute Profile) server on the ESP32 with the following Custom Service:

**Service: Helmet_Safety_Service (UUID: `181C`)**
*   **Characteristic 1: Radar_Telemetry (Notify):** Sends a tiny string when an object is detected (e.g., `DIST:30,SPD:45`).
*   **Characteristic 2: Image_Transfer (Notify/Read):** Used to send the chopped-up JPEG packets.
*   **Characteristic 3: Audio_Command (Write):** The phone writes to this characteristic to tell the ESP32 to play a specific sound out of the helmet speakers (e.g., `PLAY:TRUCK_APPROACHING`).

## 5. Smartphone Edge Compute (The App)

The mobile app does not need cellular data to do this; it runs entirely offline using the phone's native NPU (Neural Processing Unit).

1.  **Receive & Reassemble:** The app receives the BLE packets and reassembles them back into a single JPEG.
2.  **Image Classification:** The app passes the JPEG into a local Machine Learning model (CoreML for iOS, or TensorFlow Lite for Android). 
3.  **The Output:** The model uses object detection to find the largest bounding box in the frame and classifies it as `Car`, `Truck`, or `Motorcycle`.
4.  **The Alert:** The app triggers the phone's audio system to send a voice prompt ("Fast truck approaching") through the Bluetooth connection to the helmet's speakers. 

## 6. Phase 1 Prototyping Steps

1.  **The Breadboard Build:** Wire the mmWave radar to the ESP32-CAM's RX/TX pins. 
2.  **SD Card Test:** Write a script to ensure the ESP32 can reliably save video to the SD card without dropping frames.
3.  **The BLE Handshake:** Write the script that grabs a single frame on command, chunks it, and successfully reconstructs it on a laptop or phone via Bluetooth.
4.  **Sensor Fusion:** Combine the scripts so the radar serial output dictates *when* the frame is grabbed.