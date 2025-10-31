// Code to be uploaded on arduino
#include <Servo.h>

Servo ramServo;

const int potVol = A0;
const int potBright = A1;
const int joyX = A2;
const int joyY = A3;
const int joySW = 2;

const int led1 = 3, led2 = 4, led3 = 5, led4 = 6;
const int servoPin = 9;

unsigned long lastClickDebounce = 0;
const unsigned long clickDebounceMs = 200;

void setup() {
  Serial.begin(115200);           // match with Python
  pinMode(joySW, INPUT_PULLUP);
  pinMode(led1, OUTPUT);
  pinMode(led2, OUTPUT);
  pinMode(led3, OUTPUT);
  pinMode(led4, OUTPUT);
  ramServo.attach(servoPin);
  delay(200); // allow host to open port
}

void loop() {
  int volVal = analogRead(potVol);      // 0..1023
  int brightVal = analogRead(potBright);
  int xVal = analogRead(joyX);
  int yVal = analogRead(joyY);

  // joystick button (active LOW). simple debounce
  int rawBtn = !digitalRead(joySW); // pressed -> 1
  static int lastBtn = 0;
  int click = 0;
  unsigned long now = millis();
  if (rawBtn && !lastBtn && (now - lastClickDebounce > clickDebounceMs)) {
    click = 1;
    lastClickDebounce = now;
  }
  lastBtn = rawBtn;

  // Send single line: VOL:xxx,BRI:yyy,X:zzz,Y:qqq,CLK:c
  Serial.print("VOL:"); Serial.print(volVal);
  Serial.print(",BRI:"); Serial.print(brightVal);
  Serial.print(",X:"); Serial.print(xVal);
  Serial.print(",Y:"); Serial.print(yVal);
  Serial.print(",CLK:"); Serial.println(click);

  delay(50); // adjust for desired update rate

  // --- Receive processor stats from PC ---
  while (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    data.trim();
    if (data.length() == 0) continue;

    // expect "RAM:nn,tt" or "RAM:nn,TEMP:tt"
    if (data.startsWith("RAM:")) {
      int commaIndex = data.indexOf(',');
      if (commaIndex > 4) {
        String ramStr = data.substring(4, commaIndex);
        String tempStr = data.substring(commaIndex + 1);
        if (tempStr.startsWith("TEMP:")) tempStr = tempStr.substring(5);

        int ram = ramStr.toInt();
        int temp = tempStr.toInt();

        // clamp
        if (ram < 0) ram = 0; if (ram > 100) ram = 100;

        int angle = map(ram, 0, 100, 0, 180);
        ramServo.write(angle);

        digitalWrite(led1, temp < 45 ? HIGH : LOW);
        digitalWrite(led2, (temp >= 45 && temp < 60) ? HIGH : LOW);
        digitalWrite(led3, (temp >= 60 && temp < 75) ? HIGH : LOW);
        digitalWrite(led4, temp >= 75 ? HIGH : LOW);
      }
    }
  }
}
