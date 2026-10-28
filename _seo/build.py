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
import datetime, functools, html, json, pathlib, re

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
slug = lambda city: city.lower().replace(" ", "-")

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
# Gulf currencies are pegged to the dollar (the dinar to a basket), so a fixed rate stays close enough for "about"
CURRENCY = {"ae": ("AED", "درهم", 3.6725), "sa": ("SAR", "ريال سعودي", 3.75), "qa": ("QAR", "ريال قطري", 3.64),
            "kw": ("KWD", "دينار كويتي", 0.307), "bh": ("BHD", "دينار بحريني", 0.376), "om": ("OMR", "ريال عماني", 0.3845)}


def local(r, usd, lang):
    if r["code"] not in CURRENCY:
        return ""
    code, name, rate = CURRENCY[r["code"]]
    v = f"{usd * rate:.0f}" if rate > 1 else f"{usd * rate:.1f}"
    return f" (about {code} {v})" if lang == "en" else f" (نحو {v} {name})"


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


def alternates(r=None, i=None):
    if r:  # a city page: only its own English and Arabic versions
        return "".join(f'<link rel="alternate" hreflang="{l}-{r["code"].upper()}" href="{url_of(r, l)}-{slug(r["cities"][i])}">'
                       for l in (["en", "ar"] if r["arabic"] else ["en"]))
    links = [f'<link rel="alternate" hreflang="x-default" href="{SITE}/">', f'<link rel="alternate" hreflang="en" href="{SITE}/">']
    for r in REGIONS:
        links.append(f'<link rel="alternate" hreflang="en-{r["code"].upper()}" href="{url_of(r, "en")}">')
        if r["arabic"]:
            links.append(f'<link rel="alternate" hreflang="ar-{r["code"].upper()}" href="{url_of(r, "ar")}">')
    return "".join(links)


def static_blocks(page, c, lang):
    """The JS-rendered lists, written into the page for crawlers (config.js re-renders them)."""
    faqs = [(f["q"], f["a"]) for f in c["faq"]]
    page = re.sub(r"<a [^>]*data-wa[^>]*>", lambda m: m.group(0).replace('href="#"', f'href="https://wa.me/{B["whatsapp"]}"'), page)
    page = between(page, "faq", "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faqs))
    page = between(page, "plans", "".join(
        f'<div class="plan"><h3>{e(p["name"])}</h3><div class="price">${p["perHour"]}<small> {e(c["priceUnit"])}</small></div>'
        f'<ul>' + "".join(f"<li>{e(x)}</li>" for x in c["planFeatures"]) + "</ul></div>" for p in c["plans"]))
    page = between(page, "tutors", "".join(f'<article class="fc"><h3>{e(t["name"])}</h3><p>{e(t["subject"])} · {e(t["credentials"])}</p></article>' for t in c["tutors"]))
    page = between(page, "socials", "".join(f'<a href="{e(x["url"])}" target="_blank" rel="noopener me" aria-label="{e(x["name"])}" title="{e(x["name"])}" style="--brand:{e(x["color"])}"><svg viewBox="0 0 24 24" aria-hidden="true">{x["icon"]}</svg></a>' for x in c["business"]["socials"]))
    page = between(page, "regions", "".join(
        f'<li><a href="{r["code"]}-{"ar" if lang == "ar" and r["arabic"] else "en"}">{e(r["label"])}</a></li>' for r in c["regions"])
        + f'<li>{e(c.get("ui", {}).get("worldwide", "Worldwide"))}</li>')
    # same markup config.js writes, so swapping it in after load doesn't shift the layout
    b = c["business"]
    page = between(page, "wall", "".join(
        f'<div class="stat rv"><strong>{e(w["value"])}</strong><span>{e(w["label"])}</span></div>' if w["type"] == "stat" else
        f'<a class="ig rv" href="{e(b["instagram"])}" target="_blank" rel="noopener"><p>{e(w["text"])}</p><span>{e(b["instagramHandle"])} →</span></a>' if w["type"] == "instagram" else
        f'<figure class="review{" feature" if w.get("featured") else ""} rv"><span class="stars">★★★★★</span><blockquote>“{e(w["quote"])}”</blockquote>'
        f'<figcaption class="who"><b>{e(w["name"][0])}</b><div><strong>{e(w["name"])}</strong><small>{e(w["role"])}</small></div></figcaption></figure>'
        for w in c["wall"]))
    page = between(page, "plannote", e(c["planNote"]))
    page = between(page, "footsubjects", "".join(f'<li><a href="#" data-trial-subject="{e(x["label"])}">{e(x["label"])}</a></li>' for x in c["footer"]["subjects"]))
    page = between(page, "footcurricula", "".join(f"<li>{e(x)}</li>" for x in c["footer"]["curricula"]))
    page = between(page, "foottests", "".join(f"<li>{e(x)}</li>" for x in c["footer"]["tests"]))
    get = lambda path: functools.reduce(lambda o, k: (o or {}).get(k), path.split("."), c)
    page = re.sub(r'(data-cfg="([^"]+)"[^>]*>)[^<]*', lambda m: m.group(1) + e(get(m.group(2)) or ""), page)
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
EYEBROW = re.compile(r'<span data-cfg="business.enrolmentBanner">[^<]*</span>')
H1 = re.search(r"<h1>.*?</h1>", TEMPLATE).group(0)
NAV_CTA = '<button class="btn" data-open-trial data-src="nav">Book free trial</button>'

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
            title=f"Best Online Tutors in {r['label']} · {', '.join(r['cities'][:3])} · First Lesson Free · SAS Tutors",
            desc=f"Find the best online tutors in {r['full']} ({', '.join(r['cities'][:3])}). Hand-picked 1:1 tutors for {r['curricula']}, plus SAT, IMAT, BMAT and UCAT prep. From $10 an hour. First lesson free.",
            keywords=", ".join([f"online tutors in {r['label']}", f"best online tutors {r['label']}", f"best tutors in {r['label']}",
                                f"online tutoring {r['label']}", f"private tutor {r['label']}"] + [f"best tutors in {c}" for c in r["cities"]]
                               + ["online tutors", "best tutors", "best online tutors", "IGCSE tutor", "A Level tutor", "IB tutor", "SAT tutor"]),
            h1=("The best online tutors in", r["full"]),
            lead=f"Expert 1:1 online tutoring for students in {cities}. We teach {r['curricula']}, plus entry tests like SAT, IMAT, BMAT and UCAT. A hand-picked tutor, a plan built around your exam, and progress you can see after every lesson.",
            h2=f"The best online tutors for students in {r['full']}",
            intro=f"Every lesson is live and one-to-one by video, so it doesn't matter where in {r['full']} you live. Lessons are scheduled in {r['timezone']}.",
            facts=[("Curriculums", r["curricula"]), ("Lesson times", r["timezone"].capitalize() if r["timezone"].startswith("your") else r["timezone"]), ("Cities", list(range(len(r["cities"]))))],
            faq=[(f"Do you teach students in {r['full']}?", f"Yes. Every lesson is live and online, so students anywhere in {r['full']}, including {cities}, learn with the same hand-picked tutors."),
                 (f"Which curriculums do you teach in {r['full']}?", f"We teach {r['curricula']}. We also prepare students for the SAT, IMAT, BMAT and UCAT."),
                 ("What time are lessons?", f"Lessons are scheduled in {r['timezone']}, at times that suit your school day."),
                 ("How much does online tutoring cost?", f"Lessons cost $20 an hour{local(r, 20, 'en')} on the 20-hour plan, $15 an hour{local(r, 15, 'en')} on the 50-hour plan and $10 an hour{local(r, 10, 'en')} on the 100-hour plan, in US dollars converted to your local currency at checkout. Your first lesson is free.")],
            label="Tutoring in " + r["label"])
    name, full, cities_ar, tz = AR_REGION[r["code"]]
    cur = AR_CURRICULA.get(r["code"], AR_CURRICULA_GULF)
    cities = join_list(cities_ar, "و")
    return dict(
        title=f"أفضل المدرسين الخصوصيين أونلاين في {name} · {'، '.join(cities_ar[:3])} · الحصة الأولى مجانية · SAS Tutors",
        desc=f"أفضل مدرس خصوصي أونلاين لطلاب {full} ({'، '.join(cities_ar[:3])}): معلّمون مختارون بعناية في {cur}، والتحضير لاختبارات SAT وIMAT وBMAT وUCAT. من 10 دولارات للساعة. الحصة الأولى مجانية.",
        keywords="، ".join([f"مدرس خصوصي في {name}", f"أفضل مدرس خصوصي في {name}", f"معلم خصوصي أونلاين في {name}", f"دروس خصوصية أونلاين في {name}",
                            f"أفضل المدرسين في {name}"] + [f"أفضل مدرس خصوصي في {c}" for c in cities_ar]
                           + ["مدرس خصوصي أونلاين", "أفضل مدرس خصوصي", "دروس خصوصية أونلاين", "مدرس IGCSE", "مدرس رياضيات", "مدرس فيزياء"]),
        h1=("أفضل المدرسين الخصوصيين أونلاين في", full),
        lead=f"دروس خصوصية فردية أونلاين لطلاب {cities}. ندرّس {cur}، إضافةً إلى اختبارات القبول مثل SAT وIMAT وBMAT وUCAT. معلّم مختار بعناية، وخطة مبنية حول امتحانك، وتقدّم تراه بعد كل حصة.",
        h2=f"أفضل المدرسين الخصوصيين أونلاين لطلاب {full}",
        intro=f"كل حصة مباشرة وفردية عبر الفيديو، فلا يهم أين تقيم في {full}. تُجدول الحصص حسب {tz}.",
        facts=[("المناهج", cur), ("مواعيد الحصص", tz), ("المدن", list(range(len(cities_ar))))],
        faq=[(f"هل تدرّسون طلاباً في {full}؟", f"نعم. كل الحصص مباشرة وأونلاين، فيتعلّم الطلاب في أي مكان في {full}، ومنها {cities}، مع معلّمينا المختارين بعناية."),
             (f"ما المناهج التي تدرّسونها في {full}؟", f"ندرّس {cur}. ونحضّر الطلاب أيضاً لاختبارات SAT وIMAT وBMAT وUCAT."),
             ("ما مواعيد الحصص؟", f"تُجدول الحصص حسب {tz}، في أوقات تناسب يومك الدراسي."),
             ("كم تكلفة الدروس الخصوصية أونلاين؟", f"تكلفة الساعة 20 دولاراً{local(r, 20, 'ar')} في باقة 20 ساعة، و15 دولاراً{local(r, 15, 'ar')} في باقة 50 ساعة، و10 دولارات{local(r, 10, 'ar')} في باقة 100 ساعة، بالدولار الأمريكي وتُحوَّل إلى عملتك المحلية عند الدفع. وحصتك الأولى مجانية.")],
        label="دروس خصوصية في " + name)


def city_copy(r, lang, i):
    """The region copy narrowed to one city, for searches like "best tutors in Sharjah"."""
    t = region_copy(r, lang)
    others = [j for j in range(len(r["cities"])) if j != i]
    if lang == "en":
        city = r["cities"][i]
        t.update(
            title=f"Best Tutors in {city} · Online 1:1 Tutoring, First Lesson Free · SAS Tutors",
            desc=f"Find the best tutors in {city}, {r['label']}: hand-picked online 1:1 tutors for {r['curricula']}, plus SAT, IMAT, BMAT and UCAT prep. From $10 an hour. First lesson free.",
            keywords=", ".join(f"{k} {city}" for k in ["best tutors in", "best online tutors in", "online tutors in", "private tutor in", "home tutor in",
                                                        "IGCSE tutor in", "A Level tutor in", "IB tutor in", "maths tutor in"])
                     + f", best tutors in {r['label']}, online tutors, best tutors, best online tutors",
            h1=("The best online tutors in", city),
            lead=t["lead"].replace(join_list(r["cities"], "and"), city),
            h2=f"The best online tutors for students in {city}",
            intro=f"Every lesson is live and one-to-one by video, so students in {city} learn from home with the same hand-picked tutors as the rest of {r['full']}. Lessons are scheduled in {r['timezone']}.",
            facts=t["facts"][:2] + [("Also teaching in", others)],
            faq=[(f"Do you have tutors for students in {city}?", f"Yes. Every lesson is live and online, so students in {city} learn from home with the same hand-picked tutors as the rest of {r['full']}."),
                 (f"Do you offer home tutors in {city}?", f"Our tutors teach by live video with a shared whiteboard, so lessons happen at home in {city} with no travel, at times that suit your school day.")] + t["faq"][1:],
            label="Tutoring in " + city)
        return t
    name, full, cities_ar, tz = AR_REGION[r["code"]]
    city = cities_ar[i]
    t.update(
        title=f"أفضل مدرس خصوصي في {city} · دروس خصوصية أونلاين والحصة الأولى مجانية · SAS Tutors",
        desc=f"أفضل مدرس خصوصي أونلاين لطلاب {city}، {name}: معلّمون مختارون بعناية في {AR_CURRICULA.get(r['code'], AR_CURRICULA_GULF)}، والتحضير لاختبارات SAT وIMAT وBMAT وUCAT. من 10 دولارات للساعة. الحصة الأولى مجانية.",
        keywords="، ".join(f"{k} {city}" for k in ["أفضل مدرس خصوصي في", "مدرس خصوصي في", "مدرس خصوصي أونلاين في", "معلم خصوصي في",
                                                    "دروس خصوصية في", "مدرس رياضيات في", "مدرس IGCSE في"])
                 + f"، أفضل مدرس خصوصي في {name}، مدرس خصوصي أونلاين، أفضل مدرس خصوصي",
        h1=("أفضل المدرسين الخصوصيين أونلاين في", city),
        lead=t["lead"].replace(join_list(cities_ar, "و"), city),
        h2=f"أفضل المدرسين الخصوصيين أونلاين لطلاب {city}",
        intro=f"كل حصة مباشرة وفردية عبر الفيديو، فيتعلّم الطلاب في {city} من البيت مع معلّمينا المختارين بعناية. تُجدول الحصص حسب {tz}.",
        facts=t["facts"][:2] + [("ندرّس أيضاً في", others)],
        faq=[(f"هل لديكم معلّمون لطلاب {city}؟", f"نعم. كل الحصص مباشرة وأونلاين، فيتعلّم الطلاب في {city} من البيت مع معلّمينا المختارين بعناية."),
             (f"هل يوجد مدرس خصوصي في البيت في {city}؟", f"يدرّس معلّمونا عبر الفيديو المباشر مع سبورة مشتركة، فتكون الحصة في بيتك في {city} دون أي تنقّل، وفي أوقات تناسب يومك الدراسي.")] + t["faq"][1:],
        label="دروس خصوصية في " + city)
    return t


# fonts load without blocking the first paint (display=swap shows system text until they arrive)
AR_HEAD = ('<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media=\'all\'">'
           '<style>:root{--serif:"IBM Plex Sans Arabic","Bricolage Grotesque",system-ui,sans-serif;--sans:"IBM Plex Sans Arabic","Figtree",system-ui,sans-serif}'
           'html[dir=rtl] h1,html[dir=rtl] h2,html[dir=rtl] h3{letter-spacing:0}.marquee{direction:ltr}</style>')


def region_page(r, lang, i=None):
    c = CFG[lang]
    t = region_copy(r, lang) if i is None else city_copy(r, lang, i)
    url = url_of(r, lang) + ("" if i is None else "-" + slug(r["cities"][i]))
    page, faqs = static_blocks(TEMPLATE, c, lang)
    page = swap(page, f"<title>{e(cfg_title)}</title>", f"<title>{e(t['title'])}</title>")
    page = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(t["desc"])}">', page, 1)
    page = re.sub(r'<meta name="keywords" content="[^"]*">', f'<meta name="keywords" content="{e(t["keywords"])}">', page, 1)
    page = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(t["desc"])}">', page, 1)
    page = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(t["title"])}">', page, 1)
    page = swap(page, f'<meta property="og:url" content="{SITE}/">', f'<meta property="og:url" content="{url}">')
    page = swap(page, f'<link rel="canonical" href="{SITE}/">', f'<link rel="canonical" href="{url}">')
    page = between(page, "alternates", alternates(r, i) if i is not None else alternates())
    graph = [org(), service(r, "1:1 online tutoring in " + r["label"]), faq_ld(t["faq"] + faqs),
             {"@type": "BreadcrumbList", "itemListElement": [
                 {"@type": "ListItem", "position": 1, "name": B["name"], "item": SITE + "/"},
                 {"@type": "ListItem", "position": 2, "name": region_copy(r, lang)["label"], "item": url_of(r, lang)}]
                 + ([{"@type": "ListItem", "position": 3, "name": t["label"], "item": url}] if i is not None else [])}]
    page = between(page, "jsonld", ld({"@context": "https://schema.org", "@graph": graph}))
    # the slogan moves up to the eyebrow (two spans so translate() finds each half)
    page, n = EYEBROW.subn("<span><span>Master the fundamentals.</span> <span>The grades follow.</span></span>", page, 1)
    assert n, "template text missing: enrolment banner"
    page = swap(page, H1, f"<h1>{e(t['h1'][0])} <em>{e(t['h1'][1])}</em></h1>")
    if r["arabic"]:  # link the English and Arabic versions to each other
        other = "ar" if lang == "en" else "en"
        twin = url_of(r, other)[len(SITE) + 1:] + ("" if i is None else "-" + slug(r["cities"][i]))
        page = swap(page, NAV_CTA, NAV_CTA + f'<a class="lang" href="{twin}" hreflang="{other}" lang="{other}">{"العربية" if other == "ar" else "English"}</a>')
    tz = re.search(r"\(([^)/]+)", r["timezone"])
    if lang == "en":
        page = swap(page, "Physics · 4:30 PM GST", "Physics · 4:30 PM" + (" " + tz.group(1) if tz else ""))
    page = swap(page, HERO_LEAD, f'<p class="lead">{e(t["lead"])}</p>')
    names = AR_REGION[r["code"]][2] if lang == "ar" else r["cities"]
    link = lambda j: f'<a href="{r["code"]}-{lang}-{slug(r["cities"][j])}">{e(names[j])}</a>'
    facts = "".join(f"<li><b>{e(k)}</b>{' · '.join(map(link, v)) if isinstance(v, list) else e(v)}</li>" for k, v in t["facts"])
    qa = "".join(f"<details{'' if i else ' open'}><summary>{e(q)}</summary><p>{e(a)}</p></details>" for i, (q, a) in enumerate(t["faq"]))
    page = between(page, "region", f'<section id="region" style="padding-top:0"><div class="wrap faq-wrap"><div><span class="eyebrow">{e(t["label"])}</span>'
                   f'<h2 class="rv" style="margin-top:14px">{e(t["h2"])}</h2><p class="lead" style="margin-top:16px">{e(t["intro"])}</p>'
                   f'<ul class="facts">{facts}</ul></div><div>{qa}</div></div></section>')
    if lang == "ar":
        page = swap(page, '<html lang="en">', '<html lang="ar" dir="rtl">')
        page = swap(page, "</head>", AR_HEAD + "</head>")
        page = translate(page)
        page = page.replace('"Book my free trial"', '"احجز حصتي المجانية"').replace('"Continue →"', '"متابعة ←"')
        page = swap(page, "فيزياء · 4:30 مساءً بتوقيت الخليج", "فيزياء · 4:30 مساءً ب" + AR_REGION[r["code"]][3])
    return page


cfg_title = re.search(r"<title>(.*?)</title>", TEMPLATE).group(1)
cfg_title = html.unescape(cfg_title)
pages = []
for r in REGIONS:
    for lang in (["en", "ar"] if r["arabic"] else ["en"]):
        (ROOT / f"{r['code']}-{lang}.html").write_text(region_page(r, lang))
        pages.append(url_of(r, lang))
        for i, city in enumerate(r["cities"]):
            (ROOT / f"{r['code']}-{lang}-{slug(city)}.html").write_text(region_page(r, lang, i))
            pages.append(f"{url_of(r, lang)}-{slug(city)}")
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
