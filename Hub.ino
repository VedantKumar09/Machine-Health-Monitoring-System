#include <esp_now.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_wifi.h"

// Wi-Fi & Google Script Configuration
const char* ssid = "iQOO Z9";
const char* password = "12345678";
const char* scriptUrl = "https://script.google.com/macros/s/AKfycbw9eKl1GjmMnQrCUqsh1KawapM2xM5CDsXDfcOyGLJMYIiUTcQJpXInw970AlFSAvQV/exec";

// Data Struct
typedef struct {
  float temperature;
  float humidity;
  int sound;
} SensorData;

SensorData latestData;
bool dataReceived = false;

float temperature = NAN;
float humidity = NAN;
int soundLevel = 0;

unsigned long lastUploadTime = 0;
const unsigned long uploadInterval = 5000;

WiFiServer server(80);

// ESP-NOW Peer MAC Address
uint8_t nodeMac[] = {0x3c, 0x8a, 0x1f, 0x0c, 0xe5, 0xa8};

// Upload to Google Sheets
void uploadData() {
  if (!dataReceived || WiFi.status() != WL_CONNECTED) return;

  // Determine machine health status
  String health = "Good";
  if (latestData.temperature > 40 && latestData.humidity > 60 && latestData.sound > 20) {
    health = "Critical";
  } else if (latestData.temperature > 40 && latestData.humidity > 60 ) {
    health = "Warning";
  } else if (latestData.temperature > 40 && latestData.sound > 20) {
    health = "Warning";
  } else if (latestData.humidity > 60 && latestData.sound > 20) {
    health = "Warning";
  } else if (latestData.temperature > 40 || latestData.humidity > 60 || latestData.sound > 20) {
    health = "Bad";
  }

  // Construct URL with machineHealth parameter
  String url = String(scriptUrl) +
               "?temperature=" + String(latestData.temperature, 2) +
               "&humidity=" + String(latestData.humidity, 2) +
               "&sound=" + String(latestData.sound) +
               "&machineHealth=" + health;

  Serial.println("Sending data to Google Sheets:");
  Serial.println(url);

  HTTPClient http;
  http.begin(url);
  int responseCode = http.GET();

  if (responseCode > 0) {
    Serial.print("HTTP Response code: ");
    Serial.println(responseCode);
    dataReceived = false;
  } else {
    Serial.print("Error sending GET request: ");
    Serial.println(responseCode);
  }

  http.end();
}

// ESP-NOW Callback
void OnDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len == sizeof(SensorData)) {
    memcpy(&latestData, data, sizeof(SensorData));
    temperature = latestData.temperature;
    humidity = latestData.humidity;
    soundLevel = latestData.sound;
    dataReceived = true;

    Serial.printf("Received: %.1f°C | %.1f%% | Sound: %d\n", temperature, humidity, soundLevel);
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
  Serial.println("IP address: " + WiFi.localIP().toString());

  server.begin();

  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    while (true);
  }

  esp_now_register_recv_cb(OnDataRecv);

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, nodeMac, 6);
  peerInfo.channel = 1;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    while (true);
  }

  Serial.println("ESP-NOW ready");
}

void loop() {
  if (millis() - lastUploadTime >= uploadInterval) {
    uploadData();
    lastUploadTime = millis();
  }

  WiFiClient client = server.available();
  if (client) {
    String request = "";
    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        request += c;
        if (c == '\n') {
          if (request.indexOf("GET /data") >= 0) {
            client.println("HTTP/1.1 200 OK");
            client.println("Content-Type: application/json");
            client.println("Connection: close");
            client.println();
            client.printf("{\"temperature\":%.1f,\"humidity\":%.1f,\"sound\":%d}", temperature, humidity, soundLevel);
          } else {
            client.println("HTTP/1.1 200 OK");
            client.println("Content-type:text/html");
            client.println("Connection: close");
            client.println();
            client.println(R"rawliteral(
<!DOCTYPE html><html><head><meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>ESP32 Live Dashboard</title>
<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>
<style>
body { font-family: Arial; margin: 0; padding: 10px; text-align: center; }
h2 { margin-bottom: 20px; }
.container { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
.card {
  flex: 1 1 600px;
  max-width: 650px;
  padding: 20px;
  border-radius: 10px;
  box-sizing: border-box;
}
.card.ok { background-color: #e0f7e9; }
.card.warn { background-color: #fff3cd; }
.card.critical { background-color: #f8d7da; }
canvas { margin-top: 10px; width: 100%; height: 350px; }
.nav-button {
  display: inline-block;
  padding: 12px 24px;
  margin: 10px;
  background-color: #007bff;
  color: white;
  text-decoration: none;
  border-radius: 6px;
  font-weight: bold;
  transition: background-color 0.3s;
}
.nav-button:hover {
  background-color: #0056b3;
}
.button-container {
  margin: 20px 0;
}
</style>
</head><body>
<h2>ESP32 Live Data Dashboard</h2>
<div class='button-container'>
  <a href='https://www.google.com' target='_blank' class='nav-button'>Go to Google</a>
  <a href='https://github.com' target='_blank' class='nav-button'>Go to GitHub</a>
  <a href='https://docs.espressif.com/projects/esp-idf/en/latest/' target='_blank' class='nav-button'>ESP32 Docs</a>
</div>
<div class='container'>
  <div id='tempCard' class='card'><strong>Temperature: <span id='temp'>--</span> °C</strong><canvas id='tempChart'></canvas></div>
  <div id='humCard' class='card'><strong>Humidity: <span id='hum'>--</span> %</strong><canvas id='humChart'></canvas></div>
  <div id='soundCard' class='card'><strong>Sound: <span id='sound'>--</span></strong><canvas id='soundChart'></canvas></div>
</div>
<script>
const tempCard = document.getElementById('tempCard');
const humCard = document.getElementById('humCard');
const soundCard = document.getElementById('soundCard');

function updateCardStyle(card, value, threshold) {
  card.className = 'card';
  if (value > threshold * 1.5) card.classList.add('critical');
  else if (value > threshold) card.classList.add('warn');
  else card.classList.add('ok');
}

const tempChart = new Chart(document.getElementById('tempChart').getContext('2d'), {
  type: 'line', data: { labels: [], datasets: [{ label: 'Temp (°C)', borderColor: 'red', data: [], fill: false }] },
  options: { scales: { y: { beginAtZero: true } } }
});
const humChart = new Chart(document.getElementById('humChart').getContext('2d'), {
  type: 'line', data: { labels: [], datasets: [{ label: 'Humidity (%)', borderColor: 'blue', data: [], fill: false }] },
  options: { scales: { y: { beginAtZero: true } } }
});
const soundChart = new Chart(document.getElementById('soundChart').getContext('2d'), {
  type: 'line', data: { labels: [], datasets: [{ label: 'Sound Level', borderColor: 'green', data: [], fill: false }] },
  options: { scales: { y: { beginAtZero: true } } }
});

function fetchData() {
  fetch('/data').then(res => res.json()).then(d => {
    let now = new Date().toLocaleTimeString();

    document.getElementById('temp').textContent = d.temperature;
    document.getElementById('hum').textContent = d.humidity;
    document.getElementById('sound').textContent = d.sound;

    updateCardStyle(tempCard, d.temperature, 40);
    updateCardStyle(humCard, d.humidity, 60);
    updateCardStyle(soundCard, d.sound, 20);

    [tempChart, humChart, soundChart].forEach(chart => {
      if (chart.data.labels.length > 30) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
      }
    });

    tempChart.data.labels.push(now); tempChart.data.datasets[0].data.push(d.temperature); tempChart.update();
    humChart.data.labels.push(now); humChart.data.datasets[0].data.push(d.humidity); humChart.update();
    soundChart.data.labels.push(now); soundChart.data.datasets[0].data.push(d.sound); soundChart.update();
  });
}
setInterval(fetchData, 2000);
</script>
</body></html>
)rawliteral");
          }
          break;
        }
      }
    }
    delay(1);
    client.stop();
    Serial.println("Client disconnected.");
  }
}