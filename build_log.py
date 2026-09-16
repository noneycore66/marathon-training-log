#!/usr/bin/env python3
"""
Marathon Training Log builder.
Pulls activities from Strava, applies the rules in training_log_spec.md,
and renders desktop (table) + mobile (card) HTML files.

Run manually to sync: `python build_log.py`
As of Sep 2026, also runs daily via a Hermes cron job (once/day, alongside
the email/ticket check) per the user's request — see cron job
"Update marathon training log" in the default Hermes profile.
"""
import json, os, datetime, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
CREDS_PATH = os.path.expanduser("~/.hermes_strava_creds.json")

PLAN_START = datetime.date(2026, 7, 6)   # Monday, Week 1 Day 1
RACE_DATE = datetime.date(2026, 11, 29)
NUM_WEEKS = 21

THAI_DAY = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
THAI_MONTH = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
              "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
EXPECTED = {0: "weight", 1: "run", 2: "run", 3: "weight", 4: "run", 5: "rest", 6: "long_run"}

# ---------------------------------------------------------------- token refresh

def load_creds():
    creds = json.load(open(CREDS_PATH))
    if creds["expires_at"] < datetime.datetime.now().timestamp() + 300:
        data = urllib.parse.urlencode({
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": creds["refresh_token"],
        }).encode()
        req = urllib.request.Request("https://www.strava.com/oauth/token", data=data, method="POST")
        with urllib.request.urlopen(req) as resp:
            tok = json.loads(resp.read())
        creds.update({
            "access_token": tok["access_token"],
            "refresh_token": tok["refresh_token"],
            "expires_at": tok["expires_at"],
        })
        json.dump(creds, open(CREDS_PATH, "w"))
    return creds

# ---------------------------------------------------------------- fetch + process

def fetch_activities():
    creds = load_creds()
    after_ts = int(datetime.datetime.combine(PLAN_START, datetime.time.min).timestamp()) - 86400 * 2
    all_acts, page = [], 1
    while True:
        url = f"https://www.strava.com/api/v3/athlete/activities?after={after_ts}&per_page=100&page={page}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds['access_token']}"})
        with urllib.request.urlopen(req) as resp:
            batch = json.loads(resp.read())
        if not batch:
            break
        all_acts.extend(batch)
        page += 1
        if len(batch) < 100:
            break
    return [a for a in all_acts if a["type"] != "Walk"]  # exclude Walk entirely


def attributed_date(a):
    dt = datetime.datetime.fromisoformat(a["start_date_local"])
    d = dt.date()
    if dt.time() < datetime.time(4, 0):  # night-owl cutoff
        d -= datetime.timedelta(days=1)
    return d, dt


def process_activities(raw):
    out = []
    for a in raw:
        d, dt = attributed_date(a)
        pace = None
        if a["type"] == "Run" and a["distance"] > 0:
            pace_sec = a["moving_time"] / (a["distance"] / 1000)
            pace = f"{int(pace_sec // 60)}:{int(pace_sec % 60):02d}/กม."
        out.append({
            "date": d, "raw_start": a["start_date_local"], "type": a["type"], "name": a["name"],
            "distance_km": round(a["distance"] / 1000, 2), "moving_min": round(a["moving_time"] / 60),
            "avg_hr": round(a["average_heartrate"]) if a.get("average_heartrate") else None,
            "max_hr": round(a["max_heartrate"]) if a.get("max_heartrate") else None,
            "pace": pace,
        })
    return out


def is_long_run(a):
    return a["type"] == "Run" and a["moving_min"] >= 75


def build_days(activities, today):
    by_date = {}
    for a in activities:
        by_date.setdefault(a["date"], []).append(a)

    all_days = [PLAN_START + datetime.timedelta(days=i) for i in range(NUM_WEEKS * 7)]
    days = {}
    for d in all_days:
        sessions = by_date.get(d, [])
        days[d] = {"date": d, "weekday": d.weekday(), "sessions": sessions,
                    "status": None, "note_flags": [], "credited_from": None,
                    "postponed_note": None, "swap_ok": False}

    for d, rec in days.items():
        if rec["sessions"]:
            rec["status"] = "Logged"
        elif rec["weekday"] == 5:
            rec["status"] = "Rest"
        elif d >= today:
            rec["status"] = "Pending"
        else:
            rec["status"] = "Missed"

    for sun in [d for d in all_days if d.weekday() == 6]:
        mon = sun + datetime.timedelta(days=1)
        if mon not in days:
            continue
        sun_rec, mon_rec = days[sun], days[mon]
        mon_has_run = any(s["type"] == "Run" for s in mon_rec["sessions"])
        mon_has_weight = any(s["type"] == "WeightTraining" for s in mon_rec["sessions"])
        if not sun_rec["sessions"] and mon_has_run:
            sun_rec["status"] = "Postponed"
            sun_rec["postponed_note"] = f"เลื่อนไป {mon.day} {THAI_MONTH[mon.month-1]}"
            mon_rec["credited_from"] = sun
            if not mon_has_weight:
                mon_rec["note_flags"].append("weight_missed_makeup_day")
        elif any(s["type"] == "WeightTraining" for s in sun_rec["sessions"]) and mon_has_run:
            mon_rec["swap_ok"] = True

    return days, all_days


def week_index(d):
    return (d - PLAN_START).days // 7 + 1


def build_weeks(days, all_days):
    weeks = {i: {"days": [], "run_km": 0.0, "weight_min": 0, "missed": 0} for i in range(1, NUM_WEEKS + 1)}
    for d in all_days:
        wi = week_index(d)
        weeks[wi]["days"].append(days[d])

    # totals, respecting credited_from redirection (Mon makeup run credited to prev week)
    for d in all_days:
        rec = days[d]
        wi = week_index(d)
        target_wi = week_index(rec["credited_from"]) if rec["credited_from"] else wi
        for s in rec["sessions"]:
            if rec["credited_from"] and s["type"] == "Run":
                weeks[target_wi]["run_km"] += s["distance_km"]
            elif not rec["credited_from"]:
                if s["type"] == "Run":
                    weeks[wi]["run_km"] += s["distance_km"]
                elif s["type"] == "WeightTraining":
                    weeks[wi]["weight_min"] += s["moving_min"]
            else:
                if s["type"] == "WeightTraining":
                    weeks[wi]["weight_min"] += s["moving_min"]
        if rec["status"] == "Missed" or "weight_missed_makeup_day" in rec["note_flags"]:
            weeks[wi]["missed"] += 1
    return weeks


def compute_analysis(days, all_days, today):
    counts = {"weight": [0, 0], "run": [0, 0], "long_run": [0, 0]}  # [missed, total]
    for d in all_days:
        if d >= today:
            continue
        rec = days[d]
        expected = EXPECTED[rec["weekday"]]
        if expected == "rest":
            continue
        counts[expected][1] += 1
        fulfilled = rec["status"] in ("Logged", "Postponed")
        if not fulfilled:
            counts[expected][0] += 1
    if today - datetime.timedelta(days=1) in days:
        mon_rec = None
    # also count makeup-day weight misses
    for d in all_days:
        rec = days[d]
        if "weight_missed_makeup_day" in rec["note_flags"] and d < today:
            counts["weight"][0] += 1
            counts["weight"][1] += 1

    all_runs = [a for d in all_days for a in days[d]["sessions"] if a["type"] == "Run"]
    longest = max(all_runs, key=lambda a: a["distance_km"], default=None)

    total_run_km = sum(a["distance_km"] for d in all_days for a in days[d]["sessions"] if a["type"] == "Run")
    total_weight_min = sum(a["moving_min"] for d in all_days for a in days[d]["sessions"] if a["type"] == "WeightTraining")

    return {"counts": counts, "longest": longest, "total_run_km": round(total_run_km, 1), "total_weight_min": total_weight_min}


if __name__ == "__main__":
    today = datetime.date.today()
    print(f"Syncing marathon log as of {today}...")
    raw = fetch_activities()
    activities = process_activities(raw)
    json.dump([{**a, "date": a["date"].isoformat()} for a in activities],
               open(os.path.join(HERE, "activities_cache.json"), "w"), indent=2, default=str)
    print(f"Fetched {len(activities)} activities (Walk excluded).")

    days, all_days = build_days(activities, today)
    weeks = build_weeks(days, all_days)
    analysis = compute_analysis(days, all_days, today)

    from render import render_desktop, render_mobile
    desktop_html = render_desktop(days, all_days, weeks, analysis, today, PLAN_START, RACE_DATE, NUM_WEEKS)
    mobile_html = render_mobile(days, all_days, weeks, analysis, today, PLAN_START, RACE_DATE, NUM_WEEKS)

    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(desktop_html)
    open(os.path.join(HERE, "mobile.html"), "w", encoding="utf-8").write(mobile_html)
    print("Wrote index.html (desktop) and mobile.html")
