/*
 * Arduino Physical Control Surface for Agentic AI
 *
 * Hardware: Arduino UNO R3
 * Components:
 * - 16x2 LCD (Parallel mode - pins 7, 8, 9, 10, 11, 12)
 * - 1x RGB LED (Tier 0 only for now)
 * - Servo motor
 * - Buzzer
 * - 2x Buttons (Confirm, Cancel)
 * - Sensors (Pot, Temp, Light, Tilt)
 *
 * Protocol: JSON over Serial (115200 baud)
 *
 * LCD Wiring (from video):
 * VSS → GND
 * VDD → 5V
 * V0 → 10K pot center (contrast)
 * RS → Pin 7
 * R/W → GND (write mode)
 * E → Pin 8
 * DB4 → Pin 9
 * DB5 → Pin 10
 * DB6 → Pin 11
 * DB7 → Pin 12
 * LED+ → 5V
 * LED- → GND
 */

#include <LiquidCrystal.h>
#include <Servo.h>

// ==================== PIN ASSIGNMENTS ====================

// LCD Pins (RS, E, DB4, DB5, DB6, DB7)
#define LCD_RS 7
#define LCD_E 8
#define LCD_DB4 9
#define LCD_DB5 10
#define LCD_DB6 11
#define LCD_DB7 12

// RGB LED Tier 0
#define LED_T0_R 2
#define LED_T0_G 4  // Swapped - actual green wire
#define LED_T0_B 3  // Swapped - actual blue wire

// Servo
#define SERVO_PIN 5

// Buzzer
#define BUZZER_PIN 6

// Buttons
#define BTN_CONFIRM 13
#define BTN_CANCEL A0

// Sensors
#define POT_PIN A1
#define TEMP_PIN A2
#define LIGHT_PIN A3
#define TILT_PIN A6

// ==================== HARDWARE OBJECTS ====================

// Initialize LCD with pins (RS, E, DB4, DB5, DB6, DB7)
LiquidCrystal lcd(LCD_RS, LCD_E, LCD_DB4, LCD_DB5, LCD_DB6, LCD_DB7);
Servo servo;

// ==================== STATE VARIABLES ====================

unsigned long lastSensorRead = 0;
unsigned long sensorInterval = 100;  // Read sensors every 100ms

bool lastConfirmState = HIGH;
bool lastCancelState = HIGH;
bool lastTiltState = HIGH;

unsigned long lastDebounceConfirm = 0;
unsigned long lastDebounceCancel = 0;
unsigned long lastDebounceTilt = 0;
unsigned long debounceDelay = 50;

// ==================== SETUP ====================

void setup() {
  // Initialize serial
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for serial port
  }

  // Initialize LCD (cols, rows)
  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Arduino Surface");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");

  // Initialize LED pins
  pinMode(LED_T0_R, OUTPUT);
  pinMode(LED_T0_G, OUTPUT);
  pinMode(LED_T0_B, OUTPUT);

  // Initialize servo
  servo.attach(SERVO_PIN);
  servo.write(0);

  // Initialize buzzer
  pinMode(BUZZER_PIN, OUTPUT);

  // Initialize buttons with internal pullup
  pinMode(BTN_CONFIRM, INPUT_PULLUP);
  pinMode(BTN_CANCEL, INPUT_PULLUP);
  pinMode(TILT_PIN, INPUT_PULLUP);

  // Startup sequence
  startupSequence();

  // Ready display
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ready");

  // Send ready message
  Serial.println("{\"status\":\"ready\",\"device\":\"arduino_uno_r3\"}");
}

// ==================== MAIN LOOP ====================

void loop() {
  // Process serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    processCommand(command);
  }

  // Read sensors periodically
  unsigned long currentTime = millis();
  if (currentTime - lastSensorRead >= sensorInterval) {
    lastSensorRead = currentTime;
    checkButtons();
  }
}

// ==================== COMMAND PROCESSING ====================

void processCommand(String cmd) {
  cmd.trim();

  if (cmd.startsWith("LCD ")) {
    handleLCD(cmd.substring(4));
  }
  else if (cmd.startsWith("LED ")) {
    handleLED(cmd.substring(4));
  }
  else if (cmd.startsWith("SERVO ")) {
    handleServo(cmd.substring(6));
  }
  else if (cmd.startsWith("BEEP")) {
    handleBeep(cmd.substring(4));
  }
  else if (cmd.startsWith("ALERT ")) {
    handleAlert(cmd.substring(6));
  }
  else if (cmd == "CLEAR") {
    lcd.clear();
    Serial.println("{\"cmd\":\"clear\",\"status\":\"ok\"}");
  }
  else if (cmd == "STATUS") {
    sendStatus();
  }
  else if (cmd == "PING") {
    Serial.println("{\"cmd\":\"ping\",\"status\":\"ok\"}");
  }
  else {
    Serial.print("{\"error\":\"unknown_command\",\"cmd\":\"");
    Serial.print(cmd);
    Serial.println("\"}");
  }
}

// ==================== LCD HANDLER ====================

void handleLCD(String args) {
  // Format: row col text
  int firstSpace = args.indexOf(' ');
  int secondSpace = args.indexOf(' ', firstSpace + 1);

  if (firstSpace == -1 || secondSpace == -1) {
    Serial.println("{\"error\":\"invalid_lcd_args\"}");
    return;
  }

  int row = args.substring(0, firstSpace).toInt();
  int col = args.substring(firstSpace + 1, secondSpace).toInt();
  String text = args.substring(secondSpace + 1);

  if (row < 0 || row > 1 || col < 0 || col > 15) {
    Serial.println("{\"error\":\"invalid_lcd_position\"}");
    return;
  }

  lcd.setCursor(col, row);
  lcd.print(text);

  Serial.println("{\"cmd\":\"lcd\",\"status\":\"ok\"}");
}

// ==================== LED HANDLER ====================

void handleLED(String args) {
  // Format: tier r g b
  // Note: Only Tier0 supported in this version
  int spaces[3];
  int idx = 0;
  int pos = 0;

  while (idx < 3 && pos < args.length()) {
    int space = args.indexOf(' ', pos);
    if (space == -1) space = args.length();
    spaces[idx++] = space;
    pos = space + 1;
  }

  if (idx != 3) {
    Serial.println("{\"error\":\"invalid_led_args\"}");
    return;
  }

  int tier = args.substring(0, spaces[0]).toInt();
  int r = args.substring(spaces[0] + 1, spaces[1]).toInt();
  int g = args.substring(spaces[1] + 1, spaces[2]).toInt();
  int b = args.substring(spaces[2] + 1).toInt();

  if (tier != 0) {
    Serial.println("{\"error\":\"only_tier0_supported\"}");
    return;
  }

  setLED(tier, r, g, b);

  Serial.print("{\"cmd\":\"led\",\"tier\":");
  Serial.print(tier);
  Serial.println(",\"status\":\"ok\"}");
}

void setLED(int tier, int r, int g, int b) {
  if (tier == 0) {
    analogWrite(LED_T0_R, r);
    analogWrite(LED_T0_G, g);
    analogWrite(LED_T0_B, b);
  }
}

// ==================== SERVO HANDLER ====================

void handleServo(String args) {
  int position = args.toInt();

  if (position < 0 || position > 180) {
    Serial.println("{\"error\":\"invalid_servo_position\"}");
    return;
  }

  servo.write(position);
  Serial.println("{\"cmd\":\"servo\",\"status\":\"ok\"}");
}

// ==================== BUZZER HANDLER ====================

void handleBeep(String args) {
  args.trim();
  int duration = 200;
  int frequency = 1000;

  if (args.length() > 0) {
    int space = args.indexOf(' ');
    if (space != -1) {
      duration = args.substring(0, space).toInt();
      frequency = args.substring(space + 1).toInt();
    }
  }

  tone(BUZZER_PIN, frequency, duration);
  Serial.println("{\"cmd\":\"beep\",\"status\":\"ok\"}");
}

// ==================== ALERT HANDLER ====================

void handleAlert(String args) {
  args.trim();

  if (args == "success") {
    // Green LED, ascending beeps
    setLED(0, 0, 255, 0);
    tone(BUZZER_PIN, 800, 100);
    delay(120);
    tone(BUZZER_PIN, 1000, 100);
    delay(120);
    tone(BUZZER_PIN, 1200, 100);
  }
  else if (args == "warning") {
    // Yellow LED, mid beeps
    setLED(0, 255, 255, 0);
    tone(BUZZER_PIN, 1000, 200);
    delay(250);
    tone(BUZZER_PIN, 1000, 200);
  }
  else if (args == "error") {
    // Red LED, descending beeps
    setLED(0, 255, 0, 0);
    tone(BUZZER_PIN, 1200, 100);
    delay(120);
    tone(BUZZER_PIN, 1000, 100);
    delay(120);
    tone(BUZZER_PIN, 800, 100);
  }
  else if (args == "info") {
    // Blue LED, single beep
    setLED(0, 0, 0, 255);
    tone(BUZZER_PIN, 1000, 150);
  }

  Serial.println("{\"cmd\":\"alert\",\"status\":\"ok\"}");
}

// ==================== STATUS HANDLER ====================

void sendStatus() {
  int pot = analogRead(POT_PIN);
  int tempRaw = analogRead(TEMP_PIN);
  int light = analogRead(LIGHT_PIN);

  // TMP36: (voltage - 0.5) * 100
  float voltage = tempRaw * (5.0 / 1023.0);
  float tempC = (voltage - 0.5) * 100.0;

  Serial.print("{\"cmd\":\"status\",\"pot\":");
  Serial.print(pot);
  Serial.print(",\"temp_c\":");
  Serial.print(tempC, 1);
  Serial.print(",\"light\":");
  Serial.print(light);
  Serial.println("}");
}

// ==================== BUTTON MONITORING ====================

void checkButtons() {
  unsigned long currentTime = millis();

  // Confirm button
  bool confirmReading = digitalRead(BTN_CONFIRM);
  if (confirmReading != lastConfirmState) {
    lastDebounceConfirm = currentTime;
  }
  if ((currentTime - lastDebounceConfirm) > debounceDelay) {
    if (confirmReading == LOW && lastConfirmState == HIGH) {
      Serial.println("{\"event\":\"button\",\"button\":\"confirm\",\"state\":\"pressed\"}");
    }
    lastConfirmState = confirmReading;
  }

  // Cancel button
  bool cancelReading = digitalRead(BTN_CANCEL);
  if (cancelReading != lastCancelState) {
    lastDebounceCancel = currentTime;
  }
  if ((currentTime - lastDebounceCancel) > debounceDelay) {
    if (cancelReading == LOW && lastCancelState == HIGH) {
      Serial.println("{\"event\":\"button\",\"button\":\"cancel\",\"state\":\"pressed\"}");
    }
    lastCancelState = cancelReading;
  }

  // Tilt switch
  bool tiltReading = digitalRead(TILT_PIN);
  if (tiltReading != lastTiltState) {
    lastDebounceTilt = currentTime;
  }
  if ((currentTime - lastDebounceTilt) > debounceDelay) {
    if (tiltReading == LOW && lastTiltState == HIGH) {
      Serial.println("{\"event\":\"tilt\",\"triggered\":true}");
    }
    lastTiltState = tiltReading;
  }
}

// ==================== STARTUP SEQUENCE ====================

void startupSequence() {
  // LED cycle (Tier0 only)
  setLED(0, 255, 0, 0);  // Red
  delay(200);
  setLED(0, 0, 255, 0);  // Green
  delay(200);
  setLED(0, 0, 0, 255);  // Blue
  delay(200);
  setLED(0, 0, 0, 0);    // Off

  // Servo sweep
  for (int pos = 0; pos <= 180; pos += 30) {
    servo.write(pos);
    delay(100);
  }
  servo.write(0);

  // Buzzer sequence
  tone(BUZZER_PIN, 800, 100);
  delay(150);
  tone(BUZZER_PIN, 1000, 100);
  delay(150);
  tone(BUZZER_PIN, 1200, 100);
  delay(150);
}
