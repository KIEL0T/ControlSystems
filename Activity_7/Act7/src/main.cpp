#include <Arduino.h>
#include <Servo.h>

Servo myServo;
const int servoPin = 9;

void setup() {
  Serial.begin(9600);
  while (!Serial) { ; } // Wait for USB
  
  myServo.attach(servoPin);
  myServo.write(90); // Default Center
  
  Serial.println("Arduino Ready!");
}

void loop() {
  if (Serial.available() > 0) {
    String received = Serial.readStringUntil('\n');
    received.trim();

    if (received.length() == 0) return; // ignore empty input

    // Try to convert to integer
    long angle = received.toInt();

    // Check if conversion actually matches the input
    // If the input is not "0" and angle == 0, it means non-numeric
    if (angle == 0 && received != "0") {
        Serial.println("Error: Input must be numbers only!");
    }
    // Range check
    else if (angle < 0 || angle > 180) {
        Serial.println("Error: Angle must be 0-180!");
    } 
    else {
        myServo.write(angle);
        Serial.print("Moved to: ");
        Serial.println(angle);
    }
  }
}