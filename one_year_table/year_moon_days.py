import swisseph as swe
import datetime as dt
import pytz
import csv

# NOTE
# This is a draft code
# It skips Kshaya moon days at master location

# =========================
# CONFIG
# =========================

YEAR = 2026
EPHE_PATH = "."

TITHI_DEG = 12.0
AMAVASYA = 30
PURNIMA = 15

swe.set_ephe_path(EPHE_PATH)

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
    sun = swe.calc_ut(jd, swe.SUN)[0][0]
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

    hour = int(h)
    minute = int((h - hour) * 60)
    second = int((((h - hour) * 60) - minute) * 60)

    sunrise_utc = dt.datetime(y, m, d, hour, minute, second, tzinfo=pytz.UTC)
    return sunrise_utc.astimezone(tz)

def is_moon_day(date, city):
    sr = local_sunrise(date, city)
    jd = julian_day(sr.astimezone(pytz.UTC))
    t = tithi_at_jd(jd)
    return t in (AMAVASYA, PURNIMA)

# =========================
# COMPUTATION
# =========================

def moon_days_for_city(city):
    results = set()
    start = dt.date(YEAR, 1, 1)
    end = dt.date(YEAR, 12, 31)

    d = start
    while d <= end:
        if is_moon_day(d, city):
            results.add(d)
        d += dt.timedelta(days=1)

    return sorted(results)

# =========================
# CSV OUTPUT
# =========================

def generate_csv():
    print("Calculating Mysuru (master)...")
    master_days = moon_days_for_city(CITIES["Mysuru"])

    city_days = {}
    for name, city in CITIES.items():
        if name != "Mysuru":
            print(f"Calculating {name}...")
            city_days[name] = set(moon_days_for_city(city))

    headers = ["Mysuru"] + [c for c in CITIES if c != "Mysuru"]

    with open("moon_days_2026.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for d in master_days:
            row = [d.isoformat()]

            for city in headers[1:]:
                found = None
                for delta in (0, -1, 1, -2, 2):
                    candidate = d + dt.timedelta(days=delta)
                    if candidate in city_days[city]:
                        found = candidate
                        break

                if found is None:
                    row.append("NaN")
                elif found == d:
                    row.append("")
                else:
                    row.append(found.isoformat())

            writer.writerow(row)

    print("✅ CSV written: moon_days_2026.csv")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    generate_csv()

