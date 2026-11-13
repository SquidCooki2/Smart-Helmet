#include <Arduino.h>
#include <NimBLEDevice.h>
#include <SD_MMC.h>
#include "esp_camera.h"
#include "config.h"

// Shared RTOS handles
static SemaphoreHandle_t g_frameMutex = nullptr;
static TaskHandle_t g_snapshotTaskHandle = nullptr;

static NimBLECharacteristic* g_radarChar = nullptr;
static NimBLECharacteristic* g_imageChar = nullptr;
static NimBLECharacteristic* g_audioChar = nullptr;

static volatile bool g_bleConnected = false;
static unsigned long g_lastTriggerMs = 0;

class ServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* /*server*/) override {
        g_bleConnected = true;
        Serial.println("[BLE] Smartphone connected");
    }
    void onDisconnect(NimBLEServer* /*server*/) override {
        g_bleConnected = false;
        Serial.println("[BLE] Smartphone disconnected; advertising...");
        NimBLEDevice::startAdvertising();
    }
};

class AudioCommandCallbacks : public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic* pCharacteristic) override {
        std::string cmd = pCharacteristic->getValue();
        if (!cmd.empty()) {
            Serial.printf("[AUDIO_CMD] Received from phone: %s\n", cmd.c_str());
            // TODO(T-010): Route PLAY:<VEHICLE>_APPROACHING to helmet I2S/speaker amp
        }
    }
};

// Task 1: The Dashcam Loop (Core 0)
// Continuously captures frames and writes MJPEG chunks to MicroSD (3-min segments).
static void dashcamLoopTask(void* /*pvParameters*/) {
    File currentFile;
    unsigned long chunkStartMs = millis();
    uint32_t fileIndex = 0;

    for (;;) {
        camera_fb_t* fb = esp_camera_fb_get();
        if (fb != nullptr) {
            if (SD_MMC.cardType() != CARD_NONE) {
                if (!currentFile || (millis() - chunkStartMs) >= DASHCAM_CHUNK_DURATION_MS) {
                    if (currentFile) {
                        currentFile.close();
                    }
                    char path[32];
                    snprintf(path, sizeof(path), "/clip_%04lu.mjpeg", static_cast<unsigned long>(fileIndex % MAX_DASHCAM_FILES));
                    SD_MMC.remove(path); // Overwrite oldest slot when wrapping
                    currentFile = SD_MMC.open(path, FILE_WRITE);
                    chunkStartMs = millis();
                    fileIndex++;
                }
                if (currentFile) {
                    currentFile.write(fb->buf, fb->len);
                }
            }
            esp_camera_fb_return(fb);
        }
        vTaskDelay(pdMS_TO_TICKS(33)); // ~30 fps target
    }
}

// Task 3: The BLE Snapshot Handoff (Core 1)
// Wakes on radar trigger, grabs a single 320x240 JPEG, chunks into 512-byte MTU packets, and notifies phone.
static void bleSnapshotTask(void* /*pvParameters*/) {
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        if (!g_bleConnected || g_imageChar == nullptr) {
            continue;
        }

        camera_fb_t* fb = esp_camera_fb_get();
        if (fb == nullptr) {
            Serial.println("[SNAPSHOT] Failed to grab frame");
            continue;
        }

        const size_t totalLen = fb->len;
        size_t offset = 0;
        uint16_t seq = 0;
        uint8_t packet[BLE_MTU_BYTES];

        while (offset < totalLen && g_bleConnected) {
            const size_t remaining = totalLen - offset;
            const size_t chunkLen = remaining > CHUNK_PAYLOAD_MAX ? CHUNK_PAYLOAD_MAX : remaining;
            const bool isLast = (offset + chunkLen) >= totalLen;

            packet[0] = static_cast<uint8_t>(seq & 0xFF);
            packet[1] = static_cast<uint8_t>((seq >> 8) & 0xFF);
            packet[2] = isLast ? CHUNK_FLAG_EOF : 0x00;
            packet[3] = 0x00;
            memcpy(packet + CHUNK_HEADER_BYTES, fb->buf + offset, chunkLen);

            g_imageChar->setValue(packet, CHUNK_HEADER_BYTES + chunkLen);
            g_imageChar->notify();

            offset += chunkLen;
            seq++;
            vTaskDelay(pdMS_TO_TICKS(5)); // Yield briefly for BLE stack pacing
        }

        Serial.printf("[SNAPSHOT] Sent %u bytes in %u BLE packets\n",
                      static_cast<unsigned>(totalLen),
                      static_cast<unsigned>(seq));
        esp_camera_fb_return(fb);
    }
}

// Task 2: The Radar Watchdog (Core 1)
// Reads LD2410 serial stream, filters closing targets (+15 mph differential), and triggers Task 3.
static void radarWatchdogTask(void* /*pvParameters*/) {
    Serial1.begin(RADAR_BAUDRATE, SERIAL_8N1, RADAR_RX_PIN, RADAR_TX_PIN);
    String line;

    for (;;) {
        while (Serial1.available() > 0) {
            char c = static_cast<char>(Serial1.read());
            if (c == '\n') {
                line.trim();
                float distM = 0.0f;
                float speedMph = 0.0f;
                if (sscanf(line.c_str(), "DIST:%f,SPD:%f", &distM, &speedMph) == 2) {
                    const unsigned long now = millis();
                    if (distM > 0.0f && distM < DANGER_MAX_DISTANCE_M &&
                        speedMph >= DANGER_CLOSING_SPEED_MPH &&
                        (now - g_lastTriggerMs) >= TRIGGER_COOLDOWN_MS) {
                        g_lastTriggerMs = now;
                        if (g_bleConnected && g_radarChar != nullptr) {
                            char telemetry[48];
                            snprintf(telemetry, sizeof(telemetry), "DIST:%.1f,SPD:%.1f", distM, speedMph);
                            g_radarChar->setValue(reinterpret_cast<uint8_t*>(telemetry), strlen(telemetry));
                            g_radarChar->notify();
                        }
                        if (g_snapshotTaskHandle != nullptr) {
                            xTaskNotifyGive(g_snapshotTaskHandle);
                        }
                    }
                }
                line = "";
            } else {
                line += c;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

static void initBleGatt() {
    NimBLEDevice::init("SmartHelmet-ESP32");
    NimBLEDevice::setMTU(BLE_MTU_BYTES);

    NimBLEServer* server = NimBLEDevice::createServer();
    server->setCallbacks(new ServerCallbacks());

    NimBLEService* service = server->createService(HELMET_SERVICE_UUID);
    g_radarChar = service->createCharacteristic(RADAR_TELEMETRY_CHAR_UUID, NIMBLE_PROPERTY::NOTIFY);
    g_imageChar = service->createCharacteristic(IMAGE_TRANSFER_CHAR_UUID, NIMBLE_PROPERTY::NOTIFY | NIMBLE_PROPERTY::READ);
    g_audioChar = service->createCharacteristic(AUDIO_COMMAND_CHAR_UUID, NIMBLE_PROPERTY::WRITE);
    g_audioChar->setCallbacks(new AudioCommandCallbacks());

    service->start();
    NimBLEAdvertising* advertising = NimBLEDevice::getAdvertising();
    advertising->addServiceUUID(HELMET_SERVICE_UUID);
    advertising->start();
}

void setup() {
    Serial.begin(115200);
    g_frameMutex = xSemaphoreCreateMutex();

    // Note: Camera pin config depends on specific ESP32-S3 board variant (OV2640).
    // SD_MMC.begin("/sdcard", true); // 1-bit mode
    initBleGatt();

    xTaskCreatePinnedToCore(dashcamLoopTask, "DashcamLoop", 8192, nullptr, 1, nullptr, 0);
    xTaskCreatePinnedToCore(bleSnapshotTask, "BleSnapshot", 8192, nullptr, 2, &g_snapshotTaskHandle, 1);
    xTaskCreatePinnedToCore(radarWatchdogTask, "RadarWatchdog", 4096, nullptr, 2, nullptr, 1);
}

void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}
