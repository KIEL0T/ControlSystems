#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "EmonLib.h"

// =====================
// NETWORK CONFIGURATION
// =====================
const char* ssid = "ZTE_2.4G_EhRNCH";
const char* password = "fTHN7bKs";

const char* serverUrl = "http://192.168.1.16:5000/data"; 

// =====================
// HARDWARE INITIALIZATION
// =====================
EnergyMonitor emon1;             
LiquidCrystal_I2C lcd(0x27, 16, 2);

unsigned long lastTimeSent = 0;
const unsigned long sendInterval = 3000; // Send telemetry to Python every 3 seconds

void setup() {
  Serial.begin(115200);
  
  // Set up the current sensor pin (GPIO 34) and our tuned calibration factor (13.0)
  emon1.current(34, 15.5);             
  
  // Initialize LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi");

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\n📡 Wi-Fi Connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
  
  lcd.clear();
  lcd.print("WiFi Connected!");
  delay(1500);
  lcd.clear();
}

void loop() {
  // 1. Calculate RMS current based on 1480 samples
  double Irms = emon1.calcIrms(1480);  

  // 2. Custom ESP32 noise-floor gate
  if (Irms <= 0.45) {
    Irms = 0.0; 
  } else {
    Irms = Irms - 0.35; 
  }

  // 3. Calculate Power (Assuming 220V grid)
  double power = Irms * 220.0;          

  // 4. Update local I2C LCD display continuously
  lcd.setCursor(0, 0);
  lcd.print("Current: ");
  lcd.print(Irms, 3);
  lcd.print("A  ");
  
  lcd.setCursor(0, 1);
  lcd.print("Power:   ");
  lcd.print(power, 1);
  lcd.print("W  ");

  // 5. Stream telemetry to Python server at defined intervals
  if (millis() - lastTimeSent >= sendInterval) {
    lastTimeSent = millis();
    
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(serverUrl);
      
      // Sending standard url-encoded form values
      http.addHeader("Content-Type", "application/x-www-form-urlencoded");
      
      // Construct the POST data matching Flask app request.values.get("power")
      String postData = "power=" + String(power, 2);
      
      int httpResponseCode = http.POST(postData);
      
      if (httpResponseCode > 0) {
        Serial.print("📡 Sent to Flask. Status: ");
        Serial.println(httpResponseCode);
      } else {
        Serial.print("❌ HTTP POST Failed: ");
        Serial.println(http.errorToString(httpResponseCode).c_str());
      }
      
      http.end(); // Close connection
    } else {
      Serial.println("❌ Wi-Fi disconnected. Cannot send data.");
    }
  }
}