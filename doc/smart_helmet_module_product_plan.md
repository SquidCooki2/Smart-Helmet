# Product Development Plan: Aftermarket Smart Helmet Module

## 1. Executive Summary

This project outlines the development of an all-in-one, detachable smart module designed to retrofit any standard bicycle, scooter, or e-bike helmet. By combining active situational awareness, hands-free communications, emergency response, and visibility, this device targets a distinct gap in the micro-mobility safety market.

## 2. Market Positioning

Currently, cyclists must buy multiple expensive, disparate devices (e.g., Garmin Varia for radar, separate Bluetooth headsets, \$200+ integrated smart helmets) to achieve full situational awareness and connectivity.

**The Gap:** A lightweight, aerodynamic, aftermarket module that snaps onto a user's *existing* helmet, centralizing all safety and communication tech into one charging ecosystem.

## 3. Core Feature Set

* **Collision Warning System:** Rear-facing radar monitoring to alert the rider of fast-approaching vehicles.
* **Smart Object Classification:** Uses a radar-triggered camera snapshot to tell the rider exactly what is approaching (e.g., "Fast truck" vs. "Car").
* **Crash Detection & SOS:** Automatic detection of falls and automated emergency calling/texting with GPS coordinates.
* **Hands-Free Voice Control:** Triggering smartphone voice assistants to call emergency services or send messages.
* **Audio/Comms:** Delivering clear audio alerts via ear-adjacent speakers without blocking ambient traffic noise.
* **The "Black Box":** A passive, loop-recording dashcam for post-accident liability and insurance protection.
* **Visibility:** Rear lights that synchronize with the bicycle's turn indicators.

## 4. Hardware Architecture: The "Tethered Edge Compute" Model

To achieve a matchbox-sized form factor and eliminate thermal throttling, the module abandons heavy onboard AI processing in favor of a "Tethered Edge Compute" architecture. The helmet acts as a low-power sensor array, while the rider's smartphone handles the machine learning and audio rendering.

1. **The Brain (ESP32 Microcontroller):** A highly efficient, low-cost MCU that handles sensor inputs, SD card writing, and BLE transmissions.
2. **The Sentry (mmWave Radar):** A low-power mmWave radar chip runs continuously, calculating the distance and velocity of objects behind the rider natively. 
3. **The Dashcam & Snapshot Engine:** The onboard camera continuously writes a loop-recording to a local MicroSD card. When the radar detects a threat, the ESP32 grabs a single, low-resolution frame (a "snapshot") from the buffer without interrupting the recording.
4. **The Tether (BLE):** The ESP32 compresses that single snapshot into a small JPEG (approx. 15KB), chops it into data packets, and fires it over Bluetooth Low Energy to the rider's smartphone.
5. **The Smartphone NPU:** The smartphone app reassembles the image, runs a lightweight, offline AI model (CoreML/TFLite) to classify the object (Car, Truck, Motorcycle), and pushes the specific audio alert back to the helmet's speakers.

### Audio & Sensors

* **Audio Output:** Directional micro-speakers or bone-conduction transducers positioned near the temples.
* **Voice Input:** A dual-microphone array with heavy physical wind-muffing and digital noise cancellation.
* **IMU:** A 6-axis accelerometer/gyroscope to detect severe G-forces indicating a crash.

## 5. Form Factor & Mounting

* **The "Spider" Design:** To accommodate rear-facing sensors and ear-adjacent audio, the device will use a flexible "horseshoe" or "spider" shape. The central processing brain (battery, sensors, lights) mounts to the rear center of the helmet, with two thin, flexible arms routing along the bottom rim to position the speakers.
* **Power Supply:** Because the heavy AI processing is offloaded to the phone, the device can use a much smaller ~500mAh LiPo battery, drastically reducing weight and fire hazard risks on the helmet.
* **Mounting System:** An adaptive, magnetic quick-release bracket attached to the helmet via heavy-duty silicone straps (threading through helmet vents) or 3M VHB tape.
* **Weight Target:** Sub-100 grams.

## 6. Software & Connectivity Ecosystem

* **Smartphone Dependency:** The module is entirely reliant on the user's phone for AI classification, cellular data (SOS calls), GPS coordinates, and processing the audio alerts.
* **Background App Execution:** The companion iOS/Android app must be engineered with specific background execution entitlements (e.g., Bluetooth Accessory profiles) so the phone's OS does not kill the app while the phone is locked in the rider's pocket.
* **Bicycle Syncing:** Utilizes ANT+ or a secondary RF receiver to sync with a cheap, handlebar-mounted wireless remote for turn signals.

## 7. Execution Roadmap (Next Steps)

### Phase 1: Proof of Concept (The ESP32 Build)
* Wire an ESP32 development board to a generic mmWave radar, an SD-card camera module, and an IMU.
* Write the BLE GATT server firmware to successfully transmit a chunked JPEG to a phone upon a radar trigger, proving the wireless bandwidth can handle the snapshot.

### Phase 2: iOS/Android AI & Background Testing
* Develop the skeleton of the companion app to test Apple and Google's background execution limits and local CoreML/TFLite processing times.
* *Goal: Ensure the total round-trip latency (Radar -> BLE Image -> Phone AI -> Bluetooth Audio Alert) is under 1.5 seconds.*

### Phase 3: Ergonomics and Manufacturing
* 3D print dummy models of the new, smaller form factor.
* Engage an OEM/ODM (Original Design Manufacturer) specializing in wearable tech to miniaturize the PCB and source the custom batteries.