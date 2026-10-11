"""Search and AI-search build: run after editing config.json.
    python _seo/make_ar_config.py && python _seo/build.py

From index.html (the template) and config.json / config.ar.json it writes:
- index.html: JSON-LD, hreflang links and a static copy of the FAQ, plans, tutors and footer
  regions, so crawlers that don't run JavaScript (most AI crawlers) still read them.
- <cc>-en.html for every region and <cc>-ar.html (Arabic, right to left) for Arabic-speaking ones:
  the home page itself with a region title, hero line, region section and FAQ. GitHub Pages serves
  them at /ae-en, /ae-ar and so on.
- Redirect stubs for the old /online-tutors-<region>/ links, sitemap.xml, robots.txt, llms.txt.
"""
import datetime, html, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://sastutors.online"
CFG = {"en": json.loads((ROOT / "config.json").read_text()), "ar": json.loads((ROOT / "config.ar.json").read_text())}
AR_TEXT = json.loads((ROOT / "_seo" / "ar-strings.json").read_text())
cfg = CFG["en"]
B = cfg["business"]
TODAY = datetime.date.today().isoformat()
e = lambda s: html.escape(str(s), quote=True)
SUBJECTS = ["Maths", "Physics", "Chemistry", "Biology", "Statistics", "English", "Economics", "Computer Science"]
TESTS = ["SAT", "IMAT", "BMAT", "UCAT"]
REGIONS = cfg["regions"]
url_of = lambda r, lang: f"{SITE}/{r['code']}-{lang}"

# Arabic copy for region sections (country names, cities, curriculums, time zones)
AR_REGION = {
    "ae": ("الإمارات", "الإمارات", ["دبي", "أبوظبي", "الشارقة", "عجمان", "رأس الخيمة", "العين"], "توقيت الخليج"),
    "sa": ("السعودية", "السعودية", ["الرياض", "جدة", "الدمام", "الخبر", "مكة", "المدينة المنورة"], "توقيت السعودية"),
    "qa": ("قطر", "قطر", ["الدوحة", "الوكرة", "لوسيل", "الريان"], "توقيت قطر"),
    "kw": ("الكويت", "الكويت", ["مدينة الكويت", "السالمية", "حولي", "الجهراء"], "توقيت الكويت"),
    "bh": ("البحرين", "البحرين", ["المنامة", "الرفاع", "المحرق", "مدينة عيسى"], "توقيت البحرين"),
    "om": ("عُمان", "سلطنة عُمان", ["مسقط", "صلالة", "صحار", "نزوى"], "توقيت عُمان"),
    "eg": ("مصر", "مصر", ["القاهرة", "الجيزة", "الإسكندرية", "القاهرة الجديدة", "الشيخ زايد"], "توقيت مصر"),
}
AR_CURRICULA = {
    "eg": "المنهج البريطاني (IGCSE وO Level وA Level)، والدبلومة الأمريكية (مع AP وSAT)، وIB",
}
AR_CURRICULA_GULF = "المنهج البريطاني (IGCSE وGCSE وO Level وA Level)، والأمريكي (مع AP)، وIB، والهندي CBSE وISC"


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>"


def org():
    return {
        "@type": "EducationalOrganization", "@id": SITE + "/#org", "name": B["name"], "url": SITE + "/",
        "logo": SITE + "/assets/logo/icon-512.png", "image": SITE + "/assets/img/hero.webp",
        "description": B["about"], "sameAs": [x["url"] for x in B["socials"]],
        "address": {"@type": "PostalAddress", "addressCountry": "AE"},
        "areaServed": [{"@type": "Country", "name": r["label"]} for r in REGIONS],
        "contactPoint": {"@type": "ContactPoint", "contactType": "customer service", "telephone": "+" + B["whatsapp"], "availableLanguage": ["English"]},
        "knowsAbout": SUBJECTS + TESTS + ["IGCSE", "GCSE", "A Level", "IB", "AP", "CBSE", "ISC", "HSC", "VCE"],
    }


def service(area=None, name="1:1 online tutoring"):
    return {
        "@type": "Service", "name": name, "serviceType": "Online tutoring", "provider": {"@id": SITE + "/#org"},
        "areaServed": {"@type": "Country", "name": area["label"]} if area else [r["label"] for r in REGIONS],
        "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
        "offers": [{"@type": "Offer", "name": f"{p['hours']} hours", "price": p["hours"] * p["perHour"], "priceCurrency": "USD"} for p in cfg["plans"]]
                  + [{"@type": "Offer", "name": "Trial lesson", "price": 0, "priceCurrency": "USD", "description": "First lesson free"}],
    }


def faq_ld(items):
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


def between(src, name, content):
    pat = re.compile(rf"(<!--seo:{name}-->).*?(<!--/seo:{name}-->)", re.S)
    assert pat.search(src), f"marker seo:{name} missing"
    return pat.sub(lambda m: m.group(1) + content + m.group(2), src)


def swap(src, old, new):
    assert old in src, f"template text missing: {old[:60]}"
    return src.replace(old, new, 1)


def alternates():
    links = [f'<link rel="alternate" hreflang="x-default" href="{SITE}/">', f'<link rel="alternate" hreflang="en" href="{SITE}/">']
    for r in REGIONS:
        links.append(f'<link rel="alternate" hreflang="en-{r["code"].upper()}" href="{url_of(r, "en")}">')
        if r["arabic"]:
            links.append(f'<link rel="alternate" hreflang="ar-{r["code"].upper()}" href="{url_of(r, "ar")}">')
    return "".join(links)


def static_blocks(page, c, lang):
    """The JS-rendered lists, written into the page for crawlers (config.js re-renders them)."""
    faqs = [(f["q"], f["a"]) for f in c["faq"]]
    page = between(page, "faq", "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faqs))
    page = between(page, "plans", "".join(
        f'<div class="plan"><h3>{e(p["name"])}</h3><div class="price">${p["perHour"]}<small> {e(c["priceUnit"])}</small></div>'
        f'<ul>' + "".join(f"<li>{e(x)}</li>" for x in c["planFeatures"]) + "</ul></div>" for p in c["plans"]))
    page = between(page, "tutors", "".join(f'<article class="fc"><h3>{e(t["name"])}</h3><p>{e(t["subject"])} · {e(t["credentials"])}</p></article>' for t in c["tutors"]))
    page = between(page, "socials", "".join(f'<a href="{e(x["url"])}" target="_blank" rel="noopener me" aria-label="{e(x["name"])}" title="{e(x["name"])}"><svg viewBox="0 0 24 24" aria-hidden="true">{x["icon"]}</svg></a>' for x in c["business"]["socials"]))
    page = between(page, "regions", "".join(
        f'<li><a href="{r["code"]}-{"ar" if lang == "ar" and r["arabic"] else "en"}">{e(r["label"])}</a></li>' for r in c["regions"])
        + f'<li>{e(c.get("ui", {}).get("worldwide", "Worldwide"))}</li>')
    return page, faqs


def translate(page):
    """English page text → Arabic, from _seo/ar-strings.json. Leaves scripts, styles and SVG alone."""
    out, skip = [], 0
    for chunk in re.split(r"(<[^>]+>)", page):
        if chunk.startswith("<"):
            tag = re.match(r"</?\s*([a-zA-Z0-9]+)", chunk)
            name = tag.group(1).lower() if tag else ""
            if name in ("script", "style", "svg"):
                skip += -1 if chunk.startswith("</") else (0 if chunk.endswith("/>") else 1)
            chunk = re.sub(r'(placeholder|aria-label|alt|title)="([^"]*)"',
                           lambda m: f'{m.group(1)}="{e(AR_TEXT.get(html.unescape(m.group(2)), html.unescape(m.group(2))))}"', chunk)
        elif not skip and chunk.strip():
            key = " ".join(html.unescape(chunk).split())
            if key in AR_TEXT:
                lead, trail = chunk[:len(chunk) - len(chunk.lstrip())], chunk[len(chunk.rstrip()):]
                chunk = lead + e(AR_TEXT[key]) + trail
        out.append(chunk)
    return "".join(out)


TEMPLATE = (ROOT / "index.html").read_text()
HERO_LEAD = re.search(r'<p class="lead">Expert 1:1 online tutoring for American.*?</p>', TEMPLATE).group(0)
EYEBROW = '<span data-cfg="business.enrolmentBanner"></span>'

# ---- home ----------------------------------------------------------------------------------
home, faqs = static_blocks(TEMPLATE, cfg, "en")
home = between(home, "region", "")
home = between(home, "alternates", alternates())
home = between(home, "jsonld", ld({"@context": "https://schema.org", "@graph": [
    org(), {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": B["name"], "publisher": {"@id": SITE + "/#org"}},
    service(), faq_ld(faqs)]}))
(ROOT / "index.html").write_text(home)


# ---- region pages --------------------------------------------------------------------------

def join_list(items, last):
    return ", ".join(items[:-1]) + f" {last} " + items[-1] if len(items) > 1 else items[0]


def region_copy(r, lang):
    if lang == "en":
        cities = join_list(r["cities"], "and")
        return dict(
            title=f"Online Tutors in {r['label']} · Expert 1:1 Tutoring, First Lesson Free · SAS Tutors",
            desc=f"Hand-picked 1:1 online tutors for students in {r['full']} ({', '.join(r['cities'][:3])}). {r['curricula'][0].upper() + r['curricula'][1:]}, plus SAT, IMAT, BMAT and UCAT prep. From $10 an hour. First lesson free.",
            eyebrow=f"Online tutoring in {r['label']}",
            lead=f"Expert 1:1 online tutoring for students in {cities}. We teach {r['curricula']}, plus entry tests like SAT, IMAT, BMAT and UCAT. A hand-picked tutor, a plan built around your exam, and progress you can see after every lesson.",
            h2=f"Online tutoring for students in {r['full']}",
            intro=f"Every lesson is live and one-to-one by video, so it doesn't matter where in {r['full']} you live. Lessons are scheduled in {r['timezone']}.",
            facts=[("Curriculums", r["curricula"]), ("Lesson times", r["timezone"].capitalize() if r["timezone"].startswith("your") else r["timezone"]), ("Cities", cities)],
            faq=[(f"Do you teach students in {r['full']}?", f"Yes. Every lesson is live and online, so students anywhere in {r['full']}, including {cities}, learn with the same hand-picked tutors."),
                 (f"Which curriculums do you teach in {r['full']}?", f"We teach {r['curricula']}. We also prepare students for the SAT, IMAT, BMAT and UCAT."),
                 ("What time are lessons?", f"Lessons are scheduled in {r['timezone']}, at times that suit your school day."),
                 ("How much does online tutoring cost?", "Lessons cost $20 an hour on the 20-hour plan, $15 an hour on the 50-hour plan and $10 an hour on the 100-hour plan, in US dollars converted to your local currency at checkout. Your first lesson is free.")],
            label="Tutoring in " + r["label"])
    name, full, cities_ar, tz = AR_REGION[r["code"]]
    cur = AR_CURRICULA.get(r["code"], AR_CURRICULA_GULF)
    cities = join_list(cities_ar, "و")
    return dict(
        title=f"معلّمون أونلاين في {name} · دروس خصوصية فردية والحصة الأولى مجانية · SAS Tutors",
        desc=f"معلّمون خصوصيون مختارون بعناية لطلاب {full} ({'، '.join(cities_ar[:3])}): {cur}، والتحضير لاختبارات SAT وIMAT وBMAT وUCAT. من 10 دولارات للساعة. الحصة الأولى مجانية.",
        eyebrow=f"دروس خصوصية أونلاين في {name}",
        lead=f"دروس خصوصية فردية أونلاين لطلاب {cities}. ندرّس {cur}، إضافةً إلى اختبارات القبول مثل SAT وIMAT وBMAT وUCAT. معلّم مختار بعناية، وخطة مبنية حول امتحانك، وتقدّم تراه بعد كل حصة.",
        h2=f"دروس خصوصية أونلاين لطلاب {full}",
        intro=f"كل حصة مباشرة وفردية عبر الفيديو، فلا يهم أين تقيم في {full}. تُجدول الحصص حسب {tz}.",
        facts=[("المناهج", cur), ("مواعيد الحصص", tz), ("المدن", cities)],
        faq=[(f"هل تدرّسون طلاباً في {full}؟", f"نعم. كل الحصص مباشرة وأونلاين، فيتعلّم الطلاب في أي مكان في {full}، ومنها {cities}، مع معلّمينا المختارين بعناية."),
             (f"ما المناهج التي تدرّسونها في {full}؟", f"ندرّس {cur}. ونحضّر الطلاب أيضاً لاختبارات SAT وIMAT وBMAT وUCAT."),
             ("ما مواعيد الحصص؟", f"تُجدول الحصص حسب {tz}، في أوقات تناسب يومك الدراسي."),
             ("كم تكلفة الدروس الخصوصية أونلاين؟", "تكلفة الساعة 20 دولاراً في باقة 20 ساعة، و15 دولاراً في باقة 50 ساعة، و10 دولارات في باقة 100 ساعة، بالدولار الأمريكي وتُحوَّل إلى عملتك المحلية عند الدفع. وحصتك الأولى مجانية.")],
        label="دروس خصوصية في " + name)


AR_HEAD = ('<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap" rel="stylesheet">'
           '<style>:root{--serif:"IBM Plex Sans Arabic","Bricolage Grotesque",system-ui,sans-serif;--sans:"IBM Plex Sans Arabic","Figtree",system-ui,sans-serif}'
           'html[dir=rtl] h1,html[dir=rtl] h2,html[dir=rtl] h3{letter-spacing:0}.marquee{direction:ltr}</style>')


def region_page(r, lang):
    c = CFG[lang]
    t = region_copy(r, lang)
    url = url_of(r, lang)
    page, faqs = static_blocks(TEMPLATE, c, lang)
    page = swap(page, f"<title>{e(cfg_title)}</title>", f"<title>{e(t['title'])}</title>")
    page = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(t["desc"])}">', page, 1)
    page = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(t["desc"])}">', page, 1)
    page = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(t["title"])}">', page, 1)
    page = swap(page, f'<meta property="og:url" content="{SITE}/">', f'<meta property="og:url" content="{url}">')
    page = swap(page, f'<link rel="canonical" href="{SITE}/">', f'<link rel="canonical" href="{url}">')
    page = between(page, "alternates", alternates())
    graph = [org(), service(r, "1:1 online tutoring in " + r["label"]), faq_ld(t["faq"] + faqs),
             {"@type": "BreadcrumbList", "itemListElement": [
                 {"@type": "ListItem", "position": 1, "name": B["name"], "item": SITE + "/"},
                 {"@type": "ListItem", "position": 2, "name": t["label"], "item": url}]}]
    page = between(page, "jsonld", ld({"@context": "https://schema.org", "@graph": graph}))
    page = swap(page, EYEBROW, f"<span>{e(t['eyebrow'])}</span>")
    page = swap(page, HERO_LEAD, f'<p class="lead">{e(t["lead"])}</p>')
    facts = "".join(f"<li><b>{e(k)}</b>{e(v)}</li>" for k, v in t["facts"])
    qa = "".join(f"<details{'' if i else ' open'}><summary>{e(q)}</summary><p>{e(a)}</p></details>" for i, (q, a) in enumerate(t["faq"]))
    page = between(page, "region", f'<section id="region" style="padding-top:0"><div class="wrap faq-wrap"><div><span class="eyebrow">{e(t["label"])}</span>'
                   f'<h2 class="rv" style="margin-top:14px">{e(t["h2"])}</h2><p class="lead" style="margin-top:16px">{e(t["intro"])}</p>'
                   f'<ul class="facts">{facts}</ul></div><div>{qa}</div></div></section>')
    if lang == "ar":
        page = swap(page, '<html lang="en">', '<html lang="ar" dir="rtl">')
        page = swap(page, "</head>", AR_HEAD + "</head>")
        page = translate(page)
        page = page.replace('"Book my free trial"', '"احجز حصتي المجانية"').replace('"Continue →"', '"متابعة ←"')
    return page


cfg_title = re.search(r"<title>(.*?)</title>", TEMPLATE).group(1)
cfg_title = html.unescape(cfg_title)
pages = []
for r in REGIONS:
    for lang in (["en", "ar"] if r["arabic"] else ["en"]):
        (ROOT / f"{r['code']}-{lang}.html").write_text(region_page(r, lang))
        pages.append(url_of(r, lang))
    # the first region links (/online-tutors-<slug>/) were live for a day: send them on
    old = ROOT / f"online-tutors-{r['slug']}"
    old.mkdir(exist_ok=True)
    new = url_of(r, "en")
    (old / "index.html").write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved</title>'
                                    f'<link rel="canonical" href="{new}"><meta name="robots" content="noindex">'
                                    f'<meta http-equiv="refresh" content="0;url={new}"></head><body><a href="{new}">{new}</a></body></html>\n')

# ---- sitemap, robots, llms.txt ------------------------------------------------------------
urls = [SITE + "/"] + pages
(ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
(ROOT / "robots.txt").write_text(
    "# Search engines and AI assistants are welcome to read and cite this site.\n"
    "User-agent: *\nAllow: /\nDisallow: /_logo/\nDisallow: /_video/\nDisallow: /_seo/\n\n"
    + "".join(f"User-agent: {bot}\nAllow: /\n\n" for bot in
              ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot",
               "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot"])
    + f"Sitemap: {SITE}/sitemap.xml\n")
SOCIAL = " · ".join(f"{x['name']} {x['url']}" for x in B["socials"])
plans_md = "\n".join(f"- {p['hours']} hours: ${p['perHour']}/hour (${p['hours'] * p['perHour']:,} total){' · ' + p['label'] if p['label'] else ''}" for p in cfg["plans"])
(ROOT / "llms.txt").write_text(f"""# {B['name']}

> {B['about']} Expert 1:1 online tutoring by live video with hand-picked tutors. 5,000+ hours of one-to-one lessons taught. The first lesson is free.

## Key facts
- Based in: the United Arab Emirates. All lessons are online, scheduled in the student's own timezone.
- Students in: {', '.join(r['label'] for r in REGIONS)}, and worldwide.
- Subjects: {', '.join(SUBJECTS)}.
- Curriculums: American (including AP), British (IGCSE, GCSE, O Level, A Level; AQA, Edexcel, OCR, Cambridge), IB, Indian (CBSE, ISC), Australian Years 4–12 (NAPLAN, HSC, VCE), university courses.
- Entry tests: SAT, IMAT, BMAT, UCAT.
- Languages: pages in English, and in Arabic for the Gulf and Egypt.
- Contact: WhatsApp +{B['whatsapp']} · {SITE}/
- Social: {SOCIAL}

## Prices (US dollars, converted to local currency at checkout)
{plans_md}
- First lesson free. Hours never expire, can be shared with family, and work for any subject, tutor or curriculum.

## Tutors
""" + "\n".join(f"- {t['name']}: {t['subject']}. {t['credentials']}" for t in cfg["tutors"]) + f"""

## Pages
- [Home]({SITE}/): overview, tutors, prices and FAQ
""" + "\n".join(f"- [Online tutors in {r['label']}]({url_of(r, 'en')})" + (f" · [بالعربية]({url_of(r, 'ar')})" if r["arabic"] else "") for r in REGIONS) + """

## FAQ
""" + "\n".join(f"### {q}\n{a}\n" for q, a in faqs))
print(f"index.html, {len(pages)} region pages, redirects, sitemap.xml, robots.txt, llms.txt")
