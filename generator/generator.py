#!/usr/bin/env python3
import swisseph as swe
import datetime as dt
import pytz
from dataclasses import dataclass
import csv

# =========================
# CONFIG
# =========================

START_DATE = dt.date(2026, 1, 1)
END_DATE   = dt.date(2101, 1, 1)

EPHE_PATH = "./swisseph"
swe.set_ephe_path(EPHE_PATH)

MASTER_CITY = "Mysuru"
LOCAL_CITY  = "Astana"

TITHI_DEG = 12.0
PURNIMA  = 15
AMAVASYA = 30

# =========================
# CITIES
# =========================

CITIES = {
    "Mysuru": {
        "lat": 12.2958,
        "lon": 76.6394,
        "tz": "Asia/Kolkata",
    },
    "Moscow": {
        "lat": 55.7558,
        "lon": 37.6173,
        "tz": "Europe/Moscow",
    },
    "Saint-Petersburg": {
        "lat": 59.9343,
        "lon": 30.3351,
        "tz": "Europe/Moscow",
    },
    "Yekaterinburg": {
        "lat": 56.8389,
        "lon": 60.6057,
        "tz": "Asia/Yekaterinburg",
    },
    "Krasnaya Polyana": {
        "lat": 43.6828,
        "lon": 40.2596,
        "tz": "Europe/Moscow",
    },
    "Novosibirsk": {
        "lat": 55.0084,
        "lon": 82.9357,
        "tz": "Asia/Novosibirsk",
    },
    "Minsk": {
        "lat": 53.9006,
        "lon": 27.5590,
        "tz": "Europe/Minsk",
    },
    "Kyiv": {
        "lat": 50.4501,
        "lon": 30.5234,
        "tz": "Europe/Kyiv",
    },
    "Astana": {
        "lat": 51.1694,
        "lon": 71.4491,
        "tz": "Asia/Almaty",
    },
    "Almaty": {
        "lat": 43.2389,
        "lon": 76.8897,
        "tz": "Asia/Almaty",
    },
}

# =========================
# ENUMS (Arduino-compatible)
# =========================

KIND_PURNIMA         = 0
KIND_AMAVASYA        = 1
KIND_KSHAYA_PURNIMA  = 2
KIND_KSHAYA_AMAVASYA = 3

# =========================
# DATA TYPES
# =========================

@dataclass
class MoonEvent:
    index: int
    date: dt.date
    kind: int

# =========================
# ASTRONOMY
# =========================

def julian_day(dt_utc):
    return swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600,
    )

def tithi_at_jd(jd):
    sun  = swe.calc_ut(jd, swe.SUN)[0][0]
    moon = swe.calc_ut(jd, swe.MOON)[0][0]
    diff = (moon - sun) % 360.0
    return int(diff // TITHI_DEG) + 1

def local_sunrise(date, city):
    tz = pytz.timezone(city["tz"])

    local_midnight = tz.localize(
        dt.datetime(date.year, date.month, date.day, 0, 0, 0)
    )
    utc_midnight = local_midnight.astimezone(pytz.UTC)
    jd0 = julian_day(utc_midnight)

    _, tret = swe.rise_trans(
        jd0,
        swe.SUN,
        swe.CALC_RISE,
        (city["lon"], city["lat"], 0),
        atpress=0,
        attemp=0,
    )

    jd_rise = tret[0]
    y, m, d, h = swe.revjul(jd_rise, swe.GREG_CAL)

    hh = int(h)
    mm = int((h - hh) * 60)
    ss = int((((h - hh) * 60) - mm) * 60)

    return dt.datetime(y, m, d, hh, mm, ss, tzinfo=pytz.UTC).astimezone(tz)

# =========================
# EVENT KIND HELPERS
# =========================

def base_tithi(kind):
    if kind in (KIND_PURNIMA, KIND_KSHAYA_PURNIMA):
        return PURNIMA
    if kind in (KIND_AMAVASYA, KIND_KSHAYA_AMAVASYA):
        return AMAVASYA
    raise ValueError(kind)

# =========================
# EVENT DETECTION
# =========================

def detect_event(date, city):
    sr0 = local_sunrise(date, city)
    sr1 = local_sunrise(date + dt.timedelta(days=1), city)

    jd0 = julian_day(sr0.astimezone(pytz.UTC))
    jd1 = julian_day(sr1.astimezone(pytz.UTC))

    t0 = tithi_at_jd(jd0)
    t1 = tithi_at_jd(jd1)

    if t0 == PURNIMA:
        return KIND_PURNIMA
    if t0 == AMAVASYA:
        return KIND_AMAVASYA

    diff = (t1 - t0) % 30
    if diff > 1:
        skipped = [(t0 + i - 1) % 30 + 1 for i in range(1, diff)]
        if PURNIMA in skipped:
            return KIND_KSHAYA_PURNIMA
        if AMAVASYA in skipped:
            return KIND_KSHAYA_AMAVASYA

    return None

def generate_moon_days(city):
    events = []

    d = START_DATE
    last_date = None

    while d <= END_DATE:
        kind = detect_event(d, city)
        if kind is not None:
            if last_date is None or (d - last_date).days >= 2:
                events.append(MoonEvent(len(events), d, kind))
                last_date = d
        d += dt.timedelta(days=1)

    return events


# =========================
# H FILE OUTPUT
# =========================

def write_h(master, local):
    with open("moon_events.h", "w", encoding="utf-8") as f:
        f.write("// AUTO-GENERATED — DO NOT EDIT\n\n")

        f.write("enum MoonEventKind {\n")
        f.write("  PURNIMA = 0,\n")
        f.write("  AMAVASYA = 1,\n")
        f.write("  KSHAYA_PURNIMA = 2,\n")
        f.write("  KSHAYA_AMAVASYA = 3,\n")
        f.write("};\n\n")

        f.write("struct MoonEvent { int index; uint16_t y, m, d; uint8_t kind; };\n")

        f.write("const MoonEvent MASTER_EVENTS[] = {\n")
        for e in master:
            f.write(
                f"  {{{e.index}, {e.date.year}, {e.date.month}, {e.date.day}, {e.kind}}},\n"
            )
        f.write("};\n\n")

        f.write("const MoonEvent LOCAL_EVENTS[] = {\n")
        for e in local:
            f.write(
                f"  {{{e.index}, {e.date.year}, {e.date.month}, {e.date.day}, {e.kind}}},\n"
            )
        f.write("};\n\n")

# =========================
# CSV FILE OUTPUT
# =========================

MONTHS = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

def is_kshaya(kind):
    return kind in (KIND_KSHAYA_PURNIMA, KIND_KSHAYA_AMAVASYA)

def kind_label(kind):
    if kind in (KIND_PURNIMA, KIND_KSHAYA_PURNIMA):
        return "PURNIMA"
    if kind in (KIND_AMAVASYA, KIND_KSHAYA_AMAVASYA):
        return "AMAVASYA"
    raise ValueError("Unknown kind")

def fmt_date(e):
    return f"{e.date.day:02d} {MONTHS[e.date.month]} {e.date.year}"

def generate_csv(filename="moon_events.csv"):
    # --- generate events for all cities ---
    city_events = {}
    for name, city in CITIES.items():
        events = generate_moon_days(city)
        city_events[name] = events
        print(f"{name:16}: {len(events)} events")

    # --- Mysuru is the reference ---
    ref_name = MASTER_CITY
    ref_events = city_events[ref_name]

    # --- index → event map for fast lookup ---
    maps = {
        name: {e.index: e for e in events}
        for name, events in city_events.items()
    }

    city_names = list(CITIES.keys())

    # --- CSV header ---
    header = [
        f"Moon Phase",
        f"{ref_name} Date",
        *city_names[1:],
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for ref in ref_events:
            row = []

            # --- column 1: Mysuru event ---
            label = kind_label(ref.kind)
            if is_kshaya(ref.kind):
                label += " ※"
            row.append(label)

            # --- column 2: Mysuru date ---
            ref_date = fmt_date(ref)
            row.append(ref_date)

            # --- other cities ---
            for city in city_names[1:]:
                ev = maps[city].get(ref.index)

                if ev is None:
                    row.append("")
                    continue

                city_date = fmt_date(ev)

                # Case 1: local event IS kshaya
                if is_kshaya(ev.kind):
                    # Show kshaya marker only, without date
                    row.append("※")
                    continue

                # Case 2: local event falls on the same calendar date as master
                if city_date == ref_date:
                    # Same date → nothing is shown
                    row.append("")
                    continue

                # Case 3: different date and not kshaya
                row.append(city_date)

            writer.writerow(row)

    print(f"📄 CSV written to {filename}")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    master = generate_moon_days( CITIES[MASTER_CITY] )
    local  = generate_moon_days( CITIES[LOCAL_CITY] )

    write_h(master, local)

    print("✅ Generation OK")
    print(f"Mysuru events: {len(master)}")
    print(f"Local  events: {len(local)}")
    print("📦 Written to moon_events.h")

    generate_csv()
