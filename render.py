"""HTML rendering for the marathon training log (desktop table + mobile cards)."""
import datetime

THAI_DAY = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
THAI_MONTH = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
              "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]

STATUS_LABEL = {
    "weight": "เวท", "run": "วิ่ง", "long_run": "วิ่งยาว", "rest": "วันพัก",
    "Missed": "ขาดซ้อม", "Postponed": "เลื่อน", "Pending": "รอ",
}
STATUS_CLASS = {
    "weight": "tag-weight", "run": "tag-run", "long_run": "tag-longrun",
    "Rest": "tag-rest", "Missed": "tag-missed", "Postponed": "tag-postponed", "Pending": "tag-pending",
}

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');
:root{
  --paper:#f4f2ee; --ink:#1a1a1a; --hair:#ddd8cf;
  --weight:#8a5a2b; --run:#2f7d4f; --longrun:#6c3fa6; --rest:#2f5fa6;
  --missed:#c0392b; --postponed:#b8860b; --pending:#8a8a8a;
}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font-family:'Inter',sans-serif;margin:0;padding:24px;}
h1{font-family:'Bebas Neue',sans-serif;font-size:40px;letter-spacing:1px;margin:0;}
.updated{font-size:12px;color:#666;font-family:'IBM Plex Mono',monospace;}
.header-row{display:flex;justify-content:space-between;align-items:flex-end;border-bottom:3px solid var(--ink);padding-bottom:12px;margin-bottom:12px;}
.desc{font-size:13px;color:#555;margin:8px 0 16px;line-height:1.6;}
.progress-bar{background:#fff;border:1px solid var(--hair);border-radius:6px;padding:12px 16px;margin-bottom:20px;font-family:'IBM Plex Mono',monospace;font-size:13px;display:flex;gap:24px;flex-wrap:wrap;}
.progress-bar b{color:var(--ink)}
.week-title{font-family:'Bebas Neue',sans-serif;font-size:22px;letter-spacing:1px;margin-top:28px;display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--ink);padding-bottom:4px;}
.week-totals{font-family:'IBM Plex Mono',monospace;font-size:12px;color:#555;}
table{width:100%;border-collapse:collapse;margin-top:8px;table-layout:fixed;}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:#666;padding:6px 8px;border-bottom:1px solid var(--ink);}
td{padding:7px 8px;border-bottom:1px solid var(--hair);font-size:13px;vertical-align:top;}
td.num{font-family:'IBM Plex Mono',monospace;text-align:center;white-space:nowrap;}
td.note{font-size:11px;color:#777;}
tr.rest-row{background:#fafafa;}
tr.postponed-row{background:#fbf3e0;}
.pill{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:600;color:#fff;white-space:nowrap;}
.tag-weight{background:var(--weight)}
.tag-run{background:var(--run)}
.tag-longrun{background:var(--longrun)}
.tag-rest{background:var(--rest)}
.tag-missed{background:var(--missed)}
.tag-postponed{background:var(--postponed)}
.tag-pending{background:var(--pending)}
.flag{color:var(--missed);font-size:11px;font-weight:600;}
.analysis{margin-top:36px;border-top:3px solid var(--ink);padding-top:16px;}
.analysis h2{font-family:'Bebas Neue',sans-serif;font-size:26px;letter-spacing:1px;}
.analysis ul{font-family:'IBM Plex Mono',monospace;font-size:13px;line-height:1.9;padding-left:20px;}
input.notefield{width:100%;border:none;background:transparent;font-size:11px;font-family:'Inter',sans-serif;color:#555;border-bottom:1px dashed #ccc;}
"""

MOBILE_CSS = BASE_CSS + """
body{padding:12px;}
h1{font-size:30px;}
.week-card{background:#fff;border:1px solid var(--hair);border-radius:8px;margin-top:14px;overflow:hidden;}
.week-header{padding:12px 14px;font-family:'Bebas Neue',sans-serif;font-size:18px;letter-spacing:.5px;display:flex;justify-content:space-between;align-items:center;cursor:pointer;background:#efece5;}
.week-body{padding:6px 14px 12px;}
.day-card{border-bottom:1px solid var(--hair);padding:10px 0;}
.day-card:last-child{border-bottom:none;}
.day-top{display:flex;justify-content:space-between;align-items:center;font-size:13px;font-weight:600;}
.day-meta{font-family:'IBM Plex Mono',monospace;font-size:12px;color:#555;margin-top:4px;}
.session-line{font-size:12px;margin-top:3px;color:#333;}
"""


def status_pill(text, cls):
    return f'<span class="pill {cls}">{text}</span>'


def fmt_date(d):
    return f"{d.day} {THAI_MONTH[d.month-1]}"


def session_type_tag(sess_type):
    return "weight" if sess_type == "WeightTraining" else "run"


def day_program_name(rec):
    sessions = rec["sessions"]
    if not sessions:
        return "-"
    return " + ".join(s["name"] for s in sessions)


def day_status_pill(rec):
    if rec["status"] == "Logged":
        has_long = any(s["type"] == "Run" and s["moving_min"] >= 75 for s in rec["sessions"])
        has_weight = any(s["type"] == "WeightTraining" for s in rec["sessions"])
        if has_long:
            return status_pill(STATUS_LABEL["long_run"], STATUS_CLASS["long_run"])
        if any(s["type"] == "Run" for s in rec["sessions"]):
            return status_pill(STATUS_LABEL["run"], STATUS_CLASS["run"])
        if has_weight:
            return status_pill(STATUS_LABEL["weight"], STATUS_CLASS["weight"])
        return status_pill("บันทึก", "tag-run")
    if rec["status"] == "Rest":
        return status_pill(STATUS_LABEL["rest"], STATUS_CLASS["Rest"])
    if rec["status"] == "Missed":
        return status_pill(STATUS_LABEL["Missed"], STATUS_CLASS["Missed"])
    if rec["status"] == "Postponed":
        return status_pill(STATUS_LABEL["Postponed"], STATUS_CLASS["Postponed"])
    if rec["status"] == "Pending":
        return status_pill(STATUS_LABEL["Pending"], STATUS_CLASS["Pending"])
    return ""


def header_and_progress(today, plan_start, race_date, num_weeks):
    cur_week = min(num_weeks, max(1, (today - plan_start).days // 7 + 1))
    days_to_race = (race_date - today).days
    updated = f"{today.day} {THAI_MONTH[today.month-1]} {today.year+543}"
    return f"""
<div class="header-row">
  <h1>MARATHON LOG</h1>
  <div class="updated">อัปเดตล่าสุด: {updated}</div>
</div>
<div class="desc">บันทึกทุกวันตามตารางข้อมมาตรฐาน (จ.=เวท, อ.=วิ่ง, พ.=วิ่ง/cross training, พฤ.=เวท, ศ.=วิ่ง, ส.=พัก, อา.=วิ่งยาว) — วันไหนมีข้อมูลจริงจาก Strava จะลงตามนั้น วันไหนควรซ้อมแต่ไม่มีข้อมูลจะขึ้น "ขาดซ้อม"</div>
<div class="progress-bar">
  <div>แผน: <b>{num_weeks} สัปดาห์</b></div>
  <div>เริ่ม: <b>{fmt_date(plan_start)} {plan_start.year+543}</b></div>
  <div>อยู่ที่: <b>สัปดาห์ {cur_week} จาก {num_weeks}</b></div>
  <div>วันแข่ง: <b>{fmt_date(race_date)} {race_date.year+543}</b> ({'อีก ' + str(days_to_race) + ' วัน' if days_to_race >= 0 else 'ผ่านมาแล้ว'})</div>
</div>
"""


def analysis_html(analysis):
    counts = analysis["counts"]
    lines = []
    label_map = {"weight": "เวท", "run": "วิ่ง", "long_run": "วิ่งยาว"}
    for k, (missed, total) in counts.items():
        if missed > 0:
            lines.append(f"<li>ขาดซ้อม <b>{label_map[k]}</b> {missed} จาก {total} ครั้ง</li>")
    longest = analysis["longest"]
    longest_line = "ยังไม่มีข้อมูลวิ่ง"
    if longest:
        pace = longest.get("pace") or "-"
        hr = longest.get("avg_hr")
        hr_txt = f", HR เฉลี่ย {hr} bpm" if hr else ""
        longest_line = f"{fmt_date(longest['date'])} — {longest['distance_km']} กม. ({pace}{hr_txt})"
    return f"""
<div class="analysis">
  <h2>สรุปภาพรวม</h2>
  <ul>
    <li>ระยะวิ่งรวม: <b>{analysis['total_run_km']} กม.</b></li>
    <li>เวทรวม: <b>{analysis['total_weight_min']} นาที</b></li>
    {''.join(lines) if lines else '<li>ไม่มีการขาดซ้อม 🎉</li>'}
    <li>วิ่งยาวสุด: <b>{longest_line}</b></li>
    <li>ยังไม่มีข้อมูลปั่นจักรยาน (Ride) เลย</li>
  </ul>
</div>
"""


def render_desktop(days, all_days, weeks, analysis, today, plan_start, race_date, num_weeks):
    body = []
    for wi in range(1, num_weeks + 1):
        w = weeks[wi]
        week_days = w["days"]
        body.append(f"""<div class="week-title">WEEK {wi}
          <span class="week-totals">วิ่งรวม {round(w['run_km'],1)} กม. · เวท {w['weight_min']} นาที{' · ขาดซ้อม ' + str(w['missed']) + ' วัน' if w['missed'] else ''}</span></div>""")
        rows = []
        for rec in week_days:
            d = rec["date"]
            sessions = rec["sessions"]
            row_cls = "rest-row" if rec["status"] == "Rest" else ("postponed-row" if rec["status"] == "Postponed" else "")
            dist = ", ".join(f"{s['distance_km']} กม." for s in sessions if s["type"] == "Run") or "-"
            time_ = ", ".join(f"{s['moving_min']} นาที" for s in sessions) or "-"
            pace = ", ".join(s["pace"] for s in sessions if s.get("pace")) or "-"
            hr = ", ".join(str(s["avg_hr"]) + " bpm" for s in sessions if s.get("avg_hr")) or "-"
            name = day_program_name(rec) if sessions else (rec.get("postponed_note") and f"Long Run ({rec['postponed_note']})" or "Rest" if rec["status"] == "Rest" else "-")
            note = ""
            if "weight_missed_makeup_day" in rec["note_flags"]:
                note = '<span class="flag">+ เวทขาดวันนี้</span>'
            rows.append(f"""<tr class="{row_cls}">
              <td>{THAI_DAY[rec['weekday']]}</td>
              <td class="num">{fmt_date(d)}</td>
              <td>{day_status_pill(rec)}</td>
              <td>{name}</td>
              <td class="num">{dist}</td>
              <td class="num">{time_}</td>
              <td class="num">{pace}</td>
              <td class="num">{hr}</td>
              <td class="note">{note}<input class="notefield" placeholder="เพิ่มโน้ต..."></td>
            </tr>""")
        body.append(f"""<table>
          <colgroup><col style="width:9%"><col style="width:8%"><col style="width:9%"><col style="width:22%"><col style="width:9%"><col style="width:8%"><col style="width:9%"><col style="width:9%"><col style="width:17%"></colgroup>
          <thead><tr><th>วัน</th><th>วันที่</th><th>สถานะ</th><th>ชื่อ/โปรแกรม</th><th>ระยะ</th><th>เวลา</th><th>เพซ</th><th>HR เฉลี่ย</th><th>โน้ต</th></tr></thead>
          <tbody>{''.join(rows)}</tbody></table>""")

    return f"""<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8">
<title>Marathon Log</title><style>{BASE_CSS}</style></head><body>
{header_and_progress(today, plan_start, race_date, num_weeks)}
{''.join(body)}
{analysis_html(analysis)}
</body></html>"""


def render_mobile(days, all_days, weeks, analysis, today, plan_start, race_date, num_weeks):
    cur_week = min(num_weeks, max(1, (today - plan_start).days // 7 + 1))
    body = []
    for wi in range(1, num_weeks + 1):
        w = weeks[wi]
        open_attr = "open" if wi == cur_week else ""
        cards = []
        for rec in w["days"]:
            d = rec["date"]
            def _sess_line(s):
                dist_part = f'{s["distance_km"]} กม. ' if s["type"] == "Run" and s["distance_km"] else ""
                pace_part = f' · {s["pace"]}' if s.get("pace") else ""
                hr_part = f' · {s["avg_hr"]} bpm' if s.get("avg_hr") else ""
                return f'<div class="session-line">{s["name"]} — {dist_part}{s["moving_min"]} นาที{pace_part}{hr_part}</div>'
            sess_lines = "".join(_sess_line(s) for s in rec["sessions"])
            flag = '<div class="flag">+ เวทขาดวันนี้</div>' if "weight_missed_makeup_day" in rec["note_flags"] else ""
            cards.append(f"""<div class="day-card">
              <div class="day-top"><span>{THAI_DAY[rec['weekday']]} {fmt_date(d)}</span>{day_status_pill(rec)}</div>
              {sess_lines}{flag}
            </div>""")
        body.append(f"""<details class="week-card" {open_attr}>
          <summary class="week-header">WEEK {wi} <span class="week-totals">{round(w['run_km'],1)} กม. · {w['weight_min']} นาที</span></summary>
          <div class="week-body">{''.join(cards)}</div>
        </details>""")

    return f"""<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Marathon Log (Mobile)</title><style>{MOBILE_CSS}</style></head><body>
{header_and_progress(today, plan_start, race_date, num_weeks)}
{''.join(body)}
{analysis_html(analysis)}
</body></html>"""
