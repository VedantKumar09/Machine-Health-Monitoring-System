#include <esp_now.h>
#include <WiFi.h>
#include <DHT.h>
#include "esp_wifi.h"

#define DHTPIN 4
#define DHTTYPE DHT11
#define SOUND_PIN 34

DHT dht(DHTPIN, DHTTYPE);

uint8_t hubMac[] = {0xd0, 0xef, 0x76, 0x58, 0x81, 0x1c}; // Replace with actual hub MAC

typedef struct {
  float temp;
  float hum;
  int sound;
} SensorData;

SensorData sensorReadings;

void OnDataSent(const uint8_t *mac, esp_now_send_status_t status) {
  Serial.print(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
  Serial.print(" | Temp: ");
  Serial.print(sensorReadings.temp);
  Serial.print("°C | Hum: ");
  Serial.print(sensorReadings.hum);
  Serial.print("% | Sound: ");
  Serial.println(sensorReadings.sound);
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  WiFi.mode(WIFI_STA);

  // Lock to channel 1
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);

  Serial.print("Node MAC: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    while (true);
  }

  esp_now_register_send_cb(OnDataSent);

  esp_now_peer_info_t peerInfo;
  memset(&peerInfo, 0, sizeof(peerInfo));
  memcpy(peerInfo.peer_addr, hubMac, 6);
  peerInfo.channel = 1;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    while (true);
  }

  Serial.println("Node ready");
}

void loop() {
  sensorReadings.temp = dht.readTemperature();
  sensorReadings.hum = dht.readHumidity();
  sensorReadings.sound = analogRead(SOUND_PIN);

  if (isnan(sensorReadings.temp) || isnan(sensorReadings.hum)) {
    Serial.println("DHT read error!");
    delay(2000);
    return;
  }

  esp_err_t result = esp_now_send(hubMac, (uint8_t *)&sensorReadings, sizeof(sensorReadings));

  if (result != ESP_OK) {
    Serial.println("Send error");
  }

  delay(200);
}