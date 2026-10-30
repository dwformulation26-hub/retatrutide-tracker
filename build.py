"""Validate the per-drug data files and render index.html from template.html.

Usage:
  python build.py                      validate + render
  python build.py --as-of 2026-11-02   also set the "Data as of" date first
  python build.py --check              validate only (exit 1 on any problem)

A failure is fixed in the data, never here.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
# one data file per drug; the page switches between them
DATA = {"reta": HERE / "reta_data.json", "cagri": HERE / "cagri_data.json"}
LANES = {"clinic", "animal", "patent", "stopped"}
NEWS_TYPES = {"Data", "Patent", "Deal", "Corporate", "Trial", "Regulatory", "Market"}
TRIAL_STATUS = {"COMPLETED", "RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION",
                "TERMINATED", "WITHDRAWN", "SUSPENDED", "UNKNOWN"}
ESTATE_KINDS = {"compound", "use", "formulation", "process"}
CARD_TEXT =("company", "product", "api", "interval", "platform", "stage", "now")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
MONTH = re.compile(r"\d{4}-\d{2}")
PATENT_NO = re.compile(r"[A-Z]{2}\d{6,}[A-Z]\d?")
HANGUL = re.compile(r"[가-힣]")
# words that describe the research process, not the world - never shown on the page
NARRATION = re.compile(r"\b(this run|weekly run|routine|search result|snippet|fetched|EGRESS|UNVERIFIED)\b", re.I)


def bilingual(v):
    return isinstance(v, dict) and isinstance(v.get("en"), str) and v["en"].strip() and isinstance(v.get("ko"), str) and v["ko"].strip()


def check_patent(p, where, out):
    if not PATENT_NO.fullmatch(p.get("no", "")):
        out.append(f"{where}: bad patent number {p.get('no')!r}")


def validate(d):
    p = []
    for k in ("name", "originator", "foot"):
        if not bilingual((d.get("meta") or {}).get(k)):
            p.append(f"meta {k}: needs en and ko")
    techs = {a["id"] for a in d["techs"]}
    ids = set()
    for c in d["cards"]:
        cid = c.get("id", "?")
        if cid in ids:
            p.append(f"card {cid}: duplicate id")
        ids.add(cid)
        if c.get("lane") not in LANES:
            p.append(f"card {cid}: lane {c.get('lane')!r} not in {sorted(LANES)}")
        if c.get("tech") not in techs:
            p.append(f"card {cid}: tech {c.get('tech')!r} not in techs list")
        if not re.fullmatch(r"[A-Z]{2}", c.get("region", "")):
            p.append(f"card {cid}: region must be a 2-letter code")
        for k in CARD_TEXT:
            if not bilingual(c.get(k)):
                p.append(f"card {cid}: {k} needs non-empty en and ko")
            elif NARRATION.search(c[k]["en"]):
                p.append(f"card {cid}: {k} contains pipeline narration")
        for k in ("now", "interval", "platform"):
            if bilingual(c.get(k)) and not HANGUL.search(c[k]["ko"]):
                p.append(f"card {cid}: {k}.ko has no Korean text")
        # cards must stay readable at a glance
        if bilingual(c.get("stage")) and len(c["stage"]["en"]) > 28:
            p.append(f"card {cid}: stage.en is {len(c['stage']['en'])} chars (max 28) - put detail in now")
        if bilingual(c.get("now")) and len(c["now"]["en"].split()) > 32:
            p.append(f"card {cid}: now.en is {len(c['now']['en'].split())} words (max 32) - keep the latest fact only")
        if bilingual(c.get("product")) and len(c["product"]["en"]) > 40:
            p.append(f"card {cid}: product.en longer than 40 chars")
        if not MONTH.fullmatch(c.get("lastMove", "")):
            p.append(f"card {cid}: lastMove must be YYYY-MM")
        if c.get("checked") is not None and not DATE.fullmatch(c["checked"]):
            p.append(f"card {cid}: checked must be YYYY-MM-DD")
        src = c.get("src") or {}
        if not (src.get("url", "").startswith("http") and src.get("label")):
            p.append(f"card {cid}: src needs label and http(s) url")
        for pt in c.get("patents", []):
            check_patent(pt, f"card {cid}", p)
            if not bilingual(pt.get("status")):
                p.append(f"card {cid}: patent {pt.get('no')} status needs en and ko")
        for t in c.get("trials", []):
            if not re.fullmatch(r"NCT\d{8}", t.get("nct", "")):
                p.append(f"card {cid}: bad NCT {t.get('nct')}")
            if t.get("status") not in TRIAL_STATUS:
                p.append(f"card {cid}: {t.get('nct')} status {t.get('status')!r}")
        if not c.get("trials") and not bilingual(c.get("noTrial")):
            p.append(f"card {cid}: no trials and no noTrial text")
        if c.get("lane") == "clinic" and not c.get("trials"):
            p.append(f"card {cid}: lane 'clinic' needs at least one registered trial")
    for group in ("patents", "platforms"):
        seen_no = set()
        for pt in d[group]:
            where = f"{group} {pt.get('no')}"
            check_patent(pt, where, p)
            if pt.get("no") in seen_no:
                p.append(f"{where}: duplicate")
            seen_no.add(pt.get("no"))
            if not bilingual(pt.get("tech")):
                p.append(f"{where}: tech needs en and ko")
            if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", pt.get("priority", "")):
                p.append(f"{where}: priority must be YYYY-MM or YYYY-MM-DD")
            if group == "patents" and not bilingual(pt.get("status")):
                p.append(f"{where}: status needs en and ko")
    seen = set()
    for n in d["news"]:
        key = n.get("date", "?") + " " + (n.get("text", {}).get("en", "")[:40])
        if not DATE.fullmatch(n.get("date", "")):
            p.append(f"news {key}: date must be YYYY-MM-DD")
        if n.get("region") not in ("KR", "GL"):
            p.append(f"news {key}: region must be KR or GL")
        if n.get("type") not in NEWS_TYPES:
            p.append(f"news {key}: type {n.get('type')!r}")
        if not bilingual(n.get("text")) or not HANGUL.search(n["text"].get("ko", "")):
            p.append(f"news {key}: text needs en and Korean ko")
        elif NARRATION.search(n["text"]["en"]):
            p.append(f"news {key}: text contains pipeline narration")
        src = n.get("src") or {}
        if not src.get("url", "").startswith("http"):
            p.append(f"news {key}: src url missing")
        url = src.get("url")
        if url in seen:
            p.append(f"news {key}: duplicate source url (same story twice?)")
        seen.add(url)
    for no, url in d.get("patentLinks", {}).items():
        if not PATENT_NO.fullmatch(no) or not url.startswith("http"):
            p.append(f"patentLinks {no}: needs a patent number and an http(s) url")
    for k in ("competitors", "patents", "timelineTitle", "timeline"):
        if not bilingual(d.get("lede", {}).get(k)):
            p.append(f"lede {k}: needs en and ko")
    for pt in d["estate"]:
        where = f"estate {pt.get('no')}"
        check_patent(pt, where, p)
        if pt.get("kind") not in ESTATE_KINDS:
            p.append(f"{where}: kind {pt.get('kind')!r} not in {sorted(ESTATE_KINDS)}")
        for k in ("priority", "expiry"):
            if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", pt.get(k, "")):
                p.append(f"{where}: {k} must be YYYY-MM or YYYY-MM-DD")
        if pt.get("extMax") and not pt["extMax"] > pt.get("expiry", ""):
            p.append(f"{where}: extMax must be later than expiry")
        for k in ("short", "title", "granted", "note"):
            if not bilingual(pt.get(k)):
                p.append(f"{where}: {k} needs en and ko")
        if bilingual(pt.get("short")) and len(pt["short"]["en"]) > 24:
            p.append(f"{where}: short.en longer than 24 chars - it labels a chart row")
    for i, k in enumerate(d.get("keyfacts", [])):
        for f in ("value", "label", "sub"):
            if not bilingual(k.get(f)):
                p.append(f"keyfacts {i}: {f} needs en and ko")
        if not (pt.get("src") or {}).get("url", "").startswith("http"):
            p.append(f"{where}: src url missing")
    for m in d["plan"]:
        where = f"plan {m.get('date')}"
        if not re.fullmatch(r"\d{4}(-\d{2}){0,2}", m.get("date", "")):
            p.append(f"{where}: date must be YYYY, YYYY-MM or YYYY-MM-DD")
        if not isinstance(m.get("done"), bool):
            p.append(f"{where}: done must be true or false")
        elif m["done"] and m["date"] > d.get("asOf", ""):
            p.append(f"{where}: marked done but dated after asOf")
        if not bilingual(m.get("text")) or not HANGUL.search(m["text"].get("ko", "")):
            p.append(f"{where}: text needs en and Korean ko")
        elif NARRATION.search(m["text"]["en"]):
            p.append(f"{where}: text contains pipeline narration")
        if not (m.get("src") or {}).get("url", "").startswith("http"):
            p.append(f"{where}: src url missing")
    pk = d.get("pk")
    if pk:
        srcs_ok = lambda src: all(x.get("url", "").startswith("http") for x in ([src] if isinstance(src, dict) else src or [{}]))
        for k in ("title", "answer"):
            if not bilingual(pk.get(k)):
                p.append(f"pk {k}: needs en and ko")
        for k in ("judge", "caution"):
            if not bilingual((pk.get(k) or {}).get("text")):
                p.append(f"pk {k}: text needs en and ko")
        X = pk["table"]
        for k in ("title", "sub", "none"):
            if not bilingual(X.get(k)):
                p.append(f"pk table {k}: needs en and ko")
        if X["target"] not in X["days"]:
            p.append("pk table: target day must be one of the day columns")
        for r in ([X["guide"]] if X.get("guide") else []) + X["rows"]:
            where = f"pk table row {r['name']['en']}"
            if len(r["vals"]) != len(X["days"]):
                p.append(f"{where}: needs one value per day column")
            for v in r["vals"]:
                ok = v is None or (isinstance(v, (int, float)) and 0 <= v <= 100) or (isinstance(v, list) and len(v) == 2 and 0 <= v[0] <= v[1] <= 100)
                if not ok:
                    p.append(f"{where}: values must be 0-100, a [lo, hi] range or null")
            curve = r.get("pts") or [[dd, lo] for dd, lo, hi in r.get("band", [])] + [[dd, hi] for dd, lo, hi in r.get("band", [])]
            if r is not X.get("guide") and not curve:
                p.append(f"{where}: needs pts (or a band) for the chart")
            if any(len(q) != 2 or not 0 <= q[0] <= X["axis"] or not 0 <= q[1] <= 100 for q in curve):
                p.append(f"{where}: chart points must be [day 0-{X['axis']}, value 0-100]")
            for m in X.get("metrics", []):
                v = r.get(m["key"])
                if v is not None and not (isinstance(v, (int, float)) and v > 0):
                    p.append(f"{where}: {m['key']} must be a positive number or null")
                if r.get(m["key"] + "Kind") not in (None, "figure", "simulated", "calc"):
                    p.append(f"{where}: {m['key']}Kind must be figure, simulated or calc")
            if "conc" in r:
                C = X.get("chart") or {}
                if not r.get("col"):
                    p.append(f"{where}: a row with conc needs a col")
                for pt in r["conc"]:
                    if not (0 <= pt[0] <= X["axis"] and 0 <= pt[1] <= C.get("max", 0)):
                        p.append(f"{where}: conc point {pt} outside the chart axes")
            if r.get("col") is not None and r["col"] not in range(1, 6):
                p.append(f"{where}: col must be 1-5 (the five chart colours)")
            if r is not X.get("guide"):
                if not bilingual(r.get("sub")) or not srcs_ok(r.get("src")):
                    p.append(f"{where}: needs sub (en, ko) and a source url")
                if r.get("kind") not in (None, "figure", "simulated"):
                    p.append(f"{where}: kind must be figure or simulated")
        groups = set(pk.get("refGroups", {}))
        if sum(1 for r in pk["refs"] if r.get("target")) != 1:
            p.append("pk refs: exactly one row must be the weekly target")
        for r in pk["refs"]:
            where = f"pk ref {r['name']['en']}"
            if not r.get("target") and r.get("group") not in groups:
                p.append(f"{where}: group must be one of refGroups")
            if not bilingual(r.get("sub")) or not srcs_ok(r.get("src")):
                p.append(f"{where}: needs sub (en, ko) and a source url")
            for k in ("exp", "peak"):
                if r.get(k) is not None and not bilingual(r[k]):
                    p.append(f"{where}: {k} needs en and ko")
            for col, k in (r.get("kind") or {}).items():
                if col not in ("exp", "peak") or k not in ("figure", "simulated") or not r.get(col):
                    p.append(f"{where}: kind {col}={k} must tag a filled exp or peak as figure or simulated")
    dates = [n["date"] for n in d["news"]]
    if dates != sorted(dates, reverse=True):
        p.append("news must be sorted newest first")
    if not DATE.fullmatch(d.get("asOf", "")):
        p.append("asOf must be YYYY-MM-DD")
    return p


def render(all_d):
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(all_d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = tpl.replace("/*DATA*/null", blob)
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote index.html ({len(html) // 1024} KB)")
    for key, d in all_d.items():
        print(f"  {key}: {len(d['cards'])} cards, {len(d['patents'])} + {len(d['platforms'])} patents, {len(d['estate'])} originator families, "
              f"{len(d['plan'])} milestones, {len(d['news'])} news, {len(d['pk']['table']['rows'])} PK table rows, as of {d['asOf']}")


def main():
    all_d = {key: json.loads(f.read_text(encoding="utf-8")) for key, f in DATA.items()}
    if "--as-of" in sys.argv:
        for key, f in DATA.items():
            all_d[key]["asOf"] = sys.argv[sys.argv.index("--as-of") + 1]
            f.write_text(json.dumps(all_d[key], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    problems = [f"{key}: {x}" for key, d in all_d.items() for x in validate(d)]
    for x in problems:
        print("PROBLEM:", x)
    if problems:
        print(f"{len(problems)} problem(s) - fix the data, then build again")
        sys.exit(1)
    print("validation passed")
    if "--check" not in sys.argv:
        render(all_d)


if __name__ == "__main__":
    main()
