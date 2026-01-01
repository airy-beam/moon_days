#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ThreeWire.h>
#include <RtcDS1302.h>

#include "moon_days.h"

// ===== LCD =====
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ===== RGB LED =====
const int LED_R = 9;
const int LED_G = 10;
const int LED_B = 11;

// ===== RTC PINS =====
const int RST_PIN = 4;
const int CLK_PIN = 2;
const int DAT_PIN = 3;

// ===== RTC =====
ThreeWire myWire(DAT_PIN, CLK_PIN, RST_PIN);
RtcDS1302<ThreeWire> Rtc(myWire);

// ===== TIMING =====
uint32_t lastUpdateMinute = 60;

// ---------- Helpers ----------

uint32_t dateKey(uint16_t y, uint8_t m, uint8_t d) {
  return (uint32_t)y * 10000UL + (uint32_t)m * 100UL + d;
}

void setLed(uint8_t r, uint8_t g, uint8_t b) {
  analogWrite(LED_R, r);
  analogWrite(LED_G, g);
  analogWrite(LED_B, b);
}

void centerPrint(uint8_t row, const char* text) {
  uint8_t len = strlen(text);
  uint8_t col = (len >= 16) ? 0 : (16 - len) / 2;
  lcd.setCursor(col, row);
  lcd.print(text);
}

// ---------- Find events ----------

const MoonEvent* findTodayEvent(uint32_t todayKey) {
  for (uint16_t i = 0; i < sizeof(MASTER_EVENTS) / sizeof(MoonEvent); i++) {
    const MoonEvent& ev = MASTER_EVENTS[i];
    if (dateKey(ev.y, ev.m, ev.d) == todayKey) {
      return &ev;
    }
  }
  return nullptr;
}

const MoonEvent* findNextEvent(uint32_t todayKey) {
  for (uint16_t i = 0; i < sizeof(MASTER_EVENTS) / sizeof(MoonEvent); i++) {
    const MoonEvent& ev = MASTER_EVENTS[i];
    if (dateKey(ev.y, ev.m, ev.d) > todayKey) {
      return &ev;
    }
  }
  return nullptr;
}

// ---------- Display update ----------

void updateDisplay() {
  RtcDateTime now = Rtc.GetDateTime();

  uint32_t todayKey = dateKey(
    now.Year(),
    now.Month(),
    now.Day()
  );

  lcd.clear();

  // ----- Line 1: date & time -----
  char line1[21];
  snprintf(
    line1,
    sizeof(line1),
    "%02u.%02u.%04u %02u:%02u",
    now.Day(),
    now.Month(),
    now.Year(),
    now.Hour(),
    now.Minute()
  );
  centerPrint(0, line1);

  // ----- Line 2 -----
  char line2[21];

  const MoonEvent* today = findTodayEvent(todayKey);

  if (today) {
    if (today->kind == PURNIMA || today->kind == KSHAYA_PURNIMA) {
      strcpy(line2, "PURNIMA");
      setLed(255, 0, 0);
    } else if (today->kind == AMAVASYA || today->kind == KSHAYA_AMAVASYA) {
      strcpy(line2, "AMAVASYA");
      setLed(255, 0, 0);
    } else {
      strcpy(line2, "");
      setLed(0, 255, 0);
    }
  } else {
    const MoonEvent* next = findNextEvent(todayKey);
    if (next) {
      snprintf(
        line2,
        sizeof(line2),
        "Next: %02u.%02u.%04u",
        next->d,
        next->m,
        next->y
      );
    } else {
      strcpy(line2, "No events");
    }
    setLed(0, 255, 0);
  }

  centerPrint(1, line2);
}

/* ===== SETUP ===== */

void setup() {
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);

  Wire.begin();
  lcd.begin();
  lcd.backlight();

  Rtc.Begin();

  if (!Rtc.IsDateTimeValid()) {
    // RTC lost power or was never set
  
    RtcDateTime compiled(__DATE__, __TIME__);
  
    RtcDateTime adjusted(
      compiled.Year(),
      compiled.Month(),
      compiled.Day(),
      compiled.Hour(),
      compiled.Minute(),
      compiled.Second() + 10
    );
  
    Rtc.SetDateTime(adjusted);
    Serial.println("RTC time set to compile time");
  } else {
    Serial.println("RTC time already valid");
  }

  /* ===== SET TEST DATE & TIME HERE ===== */
  // YYYY, MM, DD, HH, MM, SS
  // Rtc.SetDateTime(RtcDateTime(2026, 2, 13, 21, 41, 0));
  // ↑ меняй для тестирования

  updateDisplay();
}

/* ===== LOOP ===== */

void loop() {
  RtcDateTime now = Rtc.GetDateTime();

  if (now.Minute() != lastUpdateMinute) {
    lastUpdateMinute = now.Minute();
    updateDisplay();
  }

  delay(500);
}
