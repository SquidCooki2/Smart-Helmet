# Product Development Plan: Aftermarket Smart Helmet Module

## 1. Executive Summary
This project outlines the development of an all-in-one, detachable smart module designed to retrofit any standard bicycle, scooter, or e-bike helmet. By combining active situational awareness, hands-free communications, emergency response, and visibility, this device targets a distinct gap in the micro-mobility safety market.

## 2. Market Positioning
Currently, cyclists must buy multiple expensive, disparate devices (e.g., Garmin Varia for radar, separate Bluetooth headsets, $200+ integrated smart helmets) to achieve full situational awareness and connectivity. 

**The Gap:** A lightweight, aerodynamic, aftermarket module that snaps onto a user's *existing* helmet, centralizing all safety and communication tech into one charging ecosystem.

## 3. Core Feature Set
*   **Collision Warning System:** Rear-facing environmental monitoring to alert the rider of approaching vehicles.
*   **Crash Detection & SOS:** Automatic detection of falls and automated emergency calling/texting with GPS coordinates.
*   **Hands-Free Voice Control:** Triggering smartphone voice assistants to call emergency services or send messages.
*   **Audio/Comms:** Delivering clear audio alerts and music without blocking ambient traffic noise.
*   **Visibility:** Rear lights that synchronize with the bicycle's turn indicators.

## 4. Hardware Architecture
To balance processing power, battery life, weight, and thermal dynamics, the module will utilize a highly efficient hardware ecosystem.

### Asymmetric Sensor Fusion (Radar + Camera)
Running constant AI video processing on a helmet creates unacceptable battery drain and heat. The module will use an asymmetric, radar-triggered architecture:
1.  **The Watchman (mmWave Radar):** A low-power mmWave radar chip runs continuously, calculating the distance and velocity of objects behind the rider. It is entirely weatherproof and sees through plastic casing.
2.  **The Sleeper (Camera):** A rear-facing camera and AI processor remain in a deep-sleep state to conserve battery. The camera also acts as a passive, continuous loop-recording "dashcam" to a local SD card for liability purposes.
3.  **The Triggered AI:** When the radar detects a vehicle closing at a dangerous speed differential, it wakes the AI processor.
4.  **Coarse Classification:** The processor analyzes a burst of camera frames solely to identify the object type (Car, Truck, Motorcycle) since the radar already provided the speed and distance.

### Audio & Microphones
*   **Audio Output:** Directional micro-speakers or bone-conduction transducers positioned near the temples to keep the ear canal open to environmental sounds.
*   **Voice Input:** A dual-microphone array with physical wind-muffing and digital noise cancellation to ensure clear voice commands at high speeds.

### Sensors
*   **IMU (Inertial Measurement Unit):** A 6-axis accelerometer/gyroscope to detect severe G-forces indicating a crash.

## 5. Form Factor & Mounting
*   **The "Spider" Design:** To accommodate rear-facing sensors and ear-adjacent audio, the device will use a flexible "horseshoe" or "spider" shape. The central processing brain (battery, sensors, lights) mounts to the rear center of the helmet, with two thin, flexible arms routing along the bottom rim to position the speakers near the ears.
*   **Mounting System:** A magnetic, mechanical quick-release bracket (similar to QuadLock or GoPro) attached to the helmet via industrial 3M VHB tape. This allows instant removal for charging.
*   **Weight Target:** Sub-130 grams to prevent neck fatigue and maintain safety during impacts.

## 6. Software & Connectivity
*   **Bluetooth Low Energy (BLE):** Acts as a peripheral to the rider's smartphone.
*   **Smartphone Dependency:** Relies on the user's phone for cellular data (placing SOS calls) and native Voice Assistant processing (Siri/Google Assistant).
*   **Bicycle Syncing:** Utilizes ANT+ or a secondary RF receiver to sync with a cheap, handlebar-mounted wireless remote for turn signals.
*   **Companion App:** Required for initial setup, emergency contact input, radar sensitivity adjustment, and downloading dashcam footage.

## 7. Execution Roadmap (Next Steps)

### Phase 1: Proof of Concept (The "Frankenstein" Build)
*   Wire a Raspberry Pi Zero to a generic mmWave radar, a standard USB webcam, a 6-axis IMU, and a Bluetooth module.
*   Write basic Python scripts to test the radar-interrupt logic and the IMU crash-detection thresholds.
*   *Goal: Prove the software logic works before miniaturization.*

### Phase 2: Ergonomics and Weight Testing
*   3D print dummy models of various weights (100g, 130g, 160g) and shapes.
*   Mount them to standard helmets and conduct ride tests to determine the maximum acceptable weight limit before the helmet becomes unbalanced.

### Phase 3: Manufacturing & Sourcing
*   Engage an OEM/ODM (Original Design Manufacturer) specializing in wearable tech, action cameras, or motorcycle comms.
*   Miniaturize the PCB and source custom, high-density lithium-polymer batteries shaped to fit the curved rear module.