"""ينسخ ملفات مواقيت الصلاة الشهرية من موقع وزارة الأوقاف (data/horaires-AAAA-MM.js) إلى مجلد prayers/.

يقرأ الصفحة الرئيسية لمعرفة الملفات المنشورة، ثم يحفظ كل ملف كما هو، ويكتب prayers/index.json بقائمتها.
"""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from update import fetch, URLS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "prayers"
NAME = re.compile(r"data/(horaires-(\d{4})-(\d{2}))\.js")


def main():
    OUT.mkdir(exist_ok=True)
    names = []
    for base in URLS:
        try:
            home = fetch(base)
        except Exception as e:
            print(f"تعذرت قراءة {base}: {e}")
            continue
        for stem, _, _ in NAME.findall(home):
            if stem in names:
                continue
            try:
                body = fetch(f"{base}data/{stem}.js")
            except Exception as e:
                print(f"تعذر جلب {stem}: {e}")
                continue
            if "HORAIRES" not in body or len(body) < 1000:
                print(f"تجاهل {stem}: محتوى غير متوقع")
                continue
            path = OUT / f"{stem}.js"
            if not path.exists() or path.read_text(encoding="utf-8") != body:
                path.write_text(body, encoding="utf-8")
                print(f"حُفظ {stem} ({len(body)} حرفا)")
            names.append(stem)
        if names:
            break
    have = sorted(p.stem for p in OUT.glob("horaires-*.js"))
    keep = have[-3:]  # آخر ثلاثة أشهر تكفي
    for p in OUT.glob("horaires-*.js"):
        if p.stem not in keep:
            p.unlink()
    (OUT / "index.json").write_text(json.dumps(keep) + "\n", encoding="utf-8")
    print("المتوفر:", keep)


if __name__ == "__main__":
    main()
