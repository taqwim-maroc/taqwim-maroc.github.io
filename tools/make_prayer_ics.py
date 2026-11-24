"""يولّد لكل مدينة ملف تقويم prayers/ics/<رمز>.ics فيه الصلوات الخمس من ملفات الوزارة.

يشترك فيه تقويم Google، ومع ضبط إشعار «عند وقت الحدث» يُنبَّه المستعمل عند كل صلاة.
لا يضع إلا الأشهر الحالية واللاحقة المتوفرة، ولا يعيد كتابة ملف لم يتغير محتواه.
"""
import datetime as dt, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "prayers"
OUT = SRC / "ics"
DOMAIN = "taqwim-maroc.github.io"
NAMES = ["الصبح", None, "الظهر", "العصر", "المغرب", "العشاء"]  # الشروق ليس صلاة


def load_months():
    months = []
    for p in sorted(SRC.glob("horaires-*.js")):
        txt = p.read_text(encoding="utf-8")
        m = re.search(r"\.push\((\{.*\})\)\s*;?\s*$", txt, re.S)
        if m:
            months.append(json.loads(m.group(1)))
    return months


def offset_hours(fuseau):
    m = re.match(r"GMT\s*([+-]\s*\d+)?", fuseau or "GMT")
    return int(m.group(1).replace(" ", "")) if m and m.group(1) else 0


def esc(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")


def main():
    today = dt.date.today()
    months = [m for m in load_months() if (m["annee"], m["mois"]) >= (today.year, today.month)]
    if not months:
        print("لا توجد ملفات مواقيت للشهر الحالي")
        return
    OUT.mkdir(exist_ok=True)
    cities = {}
    for mo in months:
        off = dt.timedelta(hours=offset_hours(mo.get("fuseau")))
        for v in mo["villes"]:
            c = cities.setdefault(v["c"], {"n": v["n"], "ev": []})
            for d, row in enumerate(v["h"], start=1):
                day = dt.date(mo["annee"], mo["mois"], d)
                for i, t in enumerate(row):
                    if not NAMES[i]:
                        continue
                    hh, mm = map(int, re.sub(r"[^0-9:]", "", t).split(":"))
                    start = dt.datetime.combine(day, dt.time(hh, mm)) - off
                    c["ev"].append((start, i, NAMES[i], t))
    written = 0
    keep = set()
    for code, c in cities.items():
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//taqwim-maroc//prayers//AR", "CALSCALE:GREGORIAN",
                 "METHOD:PUBLISH", "X-WR-CALNAME:" + esc(f"مواقيت الصلاة · {c['n']}"), "X-WR-TIMEZONE:Africa/Casablanca",
                 "X-WR-CALDESC:" + esc("مواقيت وزارة الأوقاف والشؤون الإسلامية"), "REFRESH-INTERVAL;VALUE=DURATION:PT12H"]
        for start, i, name, t in c["ev"]:
            s = start.strftime("%Y%m%dT%H%M00Z")
            e = (start + dt.timedelta(minutes=10)).strftime("%Y%m%dT%H%M00Z")
            lines += ["BEGIN:VEVENT", f"UID:p{code}-{s}-{i}@{DOMAIN}", f"DTSTAMP:{s}", f"DTSTART:{s}", f"DTEND:{e}",
                      "SUMMARY:" + esc(f"صلاة {name}"), "TRANSP:TRANSPARENT", "END:VEVENT"]
        lines.append("END:VCALENDAR")
        body = "\r\n".join(lines) + "\r\n"
        path = OUT / f"{int(code)}.ics"
        keep.add(path.name)
        if not path.exists() or path.read_text(encoding="utf-8") != body:
            path.write_text(body, encoding="utf-8", newline="")
            written += 1
    for p in OUT.glob("*.ics"):
        if p.name not in keep:
            p.unlink()
    print(f"ملفات مواقيت الصلاة: {len(cities)} مدينة، تغيّر منها {written}")


if __name__ == "__main__":
    main()
