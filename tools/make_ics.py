"""يولّد calendar.ics من data.json: حدث يومي باسم اليوم الهجري، وأحداث للمناسبات.

لا يضع إلا الأيام الثابتة ببلاغ الوزارة: اليوم 30 من آخر شهر لا يُكتب حتى يصدر بلاغ الشهر الموالي.
يشترك فيه تقويم Google وغيره عبر الرابط https://taqwim-maroc.github.io/calendar.ics
"""
import datetime as dt, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HM = ["محرم", "صفر", "ربيع الأول", "ربيع الآخر", "جمادى الأولى", "جمادى الآخرة",
      "رجب", "شعبان", "رمضان", "شوال", "ذو القعدة", "ذو الحجة"]
EVENTS = {(1, 1): "رأس السنة الهجرية", (1, 10): "عاشوراء", (3, 12): "عيد المولد النبوي",
          (9, 1): "فاتح رمضان", (9, 27): "ليلة القدر", (10, 1): "عيد الفطر",
          (12, 9): "يوم عرفة", (12, 10): "عيد الأضحى"}
DOMAIN = "taqwim-maroc.github.io"


def fast_on(m, d):
    if m == 1 and d == 9:
        return "صيام تاسوعاء"
    if m == 1 and d == 10:
        return "صيام عاشوراء"
    if m == 12 and d <= 8:
        return "صيام العشر من ذي الحجة"
    if m == 12 and d == 9:
        return "صيام يوم عرفة"
    if m == 10 and 2 <= d <= 7:
        return "صيام ست من شوال"
    if m != 9 and 13 <= d <= 15 and not (m == 12 and d == 13):
        return "صيام الأيام البيض"
    return ""


def esc(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")


def fold(line):
    b = line.encode("utf-8")
    out, cur = [], b""
    for ch in line:
        c = ch.encode("utf-8")
        if len(cur) + len(c) > 73:
            out.append(cur)
            cur = b" "
        cur += c
    out.append(cur)
    return b"\r\n".join(out).decode("utf-8")


def main():
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    months = sorted(data["months"], key=lambda r: (r["y"], r["m"]))
    starts = {(r["y"], r["m"]): dt.date.fromisoformat(r["start"]) for r in months}
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//taqwim-maroc//hijri//AR", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "X-WR-CALNAME:التقويم الهجري المغربي", "X-WR-TIMEZONE:Africa/Casablanca",
             "X-WR-CALDESC:" + esc("التاريخ الهجري بالمغرب حسب بلاغات وزارة الأوقاف والشؤون الإسلامية"),
             "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for (y, m), start in starts.items():
        nxt = starts.get((y, m + 1) if m < 12 else (y + 1, 1))
        if nxt is None and (y, m) != max(starts):
            continue  # شهر ناقص البيانات قبله فجوة: لا نعرف طوله
        length = (nxt - start).days if nxt else 29
        for d in range(1, length + 1):
            day = start + dt.timedelta(days=d - 1)
            ds = day.strftime("%Y%m%d")
            end = (day + dt.timedelta(days=1)).strftime("%Y%m%d")
            title = f"{d} {HM[m - 1]} {y}هـ"
            ev = EVENTS.get((m, d))
            fs = fast_on(m, d)
            items = [("d", title)] + ([("e", f"{ev} · {title}")] if ev else [])
            if fs and fs != "صيام عاشوراء":
                items.append(("f", f"{fs} (مستحب)"))
            for kind, summary in items:
                lines += ["BEGIN:VEVENT", f"UID:{kind}-{ds}@{DOMAIN}", f"DTSTAMP:{stamp}",
                          f"DTSTART;VALUE=DATE:{ds}", f"DTEND;VALUE=DATE:{end}",
                          "SUMMARY:" + esc(summary), "TRANSP:TRANSPARENT", "END:VEVENT"]
            if d == 29:
                # مساء اليوم 29 تراقب الوزارة هلال الشهر الموالي (حدث بتوقيت ليتلقى إشعارا)
                nm = HM[m % 12]
                t0 = day.strftime("%Y%m%d") + "T190000Z"
                t1 = day.strftime("%Y%m%d") + "T200000Z"
                lines += ["BEGIN:VEVENT", f"UID:h-{ds}@{DOMAIN}", f"DTSTAMP:{stamp}",
                          f"DTSTART:{t0}", f"DTEND:{t1}",
                          "SUMMARY:" + esc(f"مراقبة هلال {nm} الليلة"),
                          "DESCRIPTION:" + esc("يصدر بلاغ وزارة الأوقاف بعد المغرب: إما غدا فاتح الشهر، وإما يُتمّ الشهر 30 يوما. افتح التطبيق واضغط «تحديث»: https://taqwim-maroc.github.io"),
                          "TRANSP:TRANSPARENT", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    body = "\r\n".join(fold(l) for l in lines) + "\r\n"
    # لا نغيّر الملف إن لم يتغير إلا الطابع الزمني، تفاديا لإيداع لا داعي له
    path = ROOT / "calendar.ics"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    strip = lambda s: "\n".join(l for l in s.splitlines() if not l.startswith("DTSTAMP"))
    if strip(old) != strip(body):
        path.write_text(body, encoding="utf-8", newline="")
        print("calendar.ics: حُدّث")
    else:
        print("calendar.ics: بلا تغيير")


if __name__ == "__main__":
    main()
