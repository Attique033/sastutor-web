"""Search and AI-search build: run after editing config.json.
    python _seo/build.py

Writes, all from config.json:
- index.html: JSON-LD (organization, service + prices, FAQ) and a static copy of the FAQ, plans,
  tutors and footer regions inside their containers, so crawlers that don't run JavaScript
  (most AI crawlers) still read them. config.js re-renders the same content in the browser.
- online-tutors-<region>/index.html: one landing page per region.
- sitemap.xml, robots.txt, llms.txt.
"""
import datetime, html, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://sastutors.online"
cfg = json.loads((ROOT / "config.json").read_text())
B = cfg["business"]
TODAY = datetime.date.today().isoformat()
e = lambda s: html.escape(str(s), quote=True)
WA = f"https://wa.me/{B['whatsapp']}?text=" + B["whatsappGreeting"].replace(" ", "%20")
SUBJECTS = ["Maths", "Physics", "Chemistry", "Biology", "Statistics", "English", "Economics", "Computer Science"]
TESTS = ["SAT", "IMAT", "BMAT", "UCAT"]


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>"


def org():
    return {
        "@type": "EducationalOrganization", "@id": SITE + "/#org", "name": B["name"], "url": SITE + "/",
        "logo": SITE + "/assets/logo/icon-512.png", "image": SITE + "/assets/img/hero.webp",
        "description": B["about"], "sameAs": [B["instagram"]],
        "address": {"@type": "PostalAddress", "addressCountry": "AE"},
        "areaServed": [{"@type": "Country", "name": r["label"]} for r in cfg["regions"]],
        "contactPoint": {"@type": "ContactPoint", "contactType": "customer service", "telephone": "+" + B["whatsapp"],
                         "availableLanguage": ["English"]},
        "knowsAbout": SUBJECTS + TESTS + ["IGCSE", "GCSE", "A Level", "IB", "AP", "CBSE", "ISC", "HSC", "VCE"],
    }


def service(area=None):
    return {
        "@type": "Service", "name": "1:1 online tutoring" + (f" in {area['label']}" if area else ""),
        "serviceType": "Online tutoring", "provider": {"@id": SITE + "/#org"},
        "areaServed": {"@type": "Country", "name": area["label"]} if area else [r["label"] for r in cfg["regions"]],
        "audience": {"@type": "EducationalAudience", "educationalRole": "student"},
        "offers": [{"@type": "Offer", "name": f"{p['hours']} hours", "price": p["hours"] * p["perHour"], "priceCurrency": "USD",
                    "description": f"{p['hours']} hours of 1:1 tutoring at ${p['perHour']} an hour"} for p in cfg["plans"]]
                  + [{"@type": "Offer", "name": "Trial lesson", "price": 0, "priceCurrency": "USD", "description": "First lesson free"}],
    }


def faq_ld(items):
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


# ---- index.html ----------------------------------------------------------------------------

def between(src, name, content):
    """Replaces what sits between <!--seo:name--> and <!--/seo:name--> (markers must exist)."""
    pat = re.compile(rf"(<!--seo:{name}-->).*?(<!--/seo:{name}-->)", re.S)
    assert pat.search(src), f"marker seo:{name} missing"
    return pat.sub(lambda m: m.group(1) + content + m.group(2), src)


page = (ROOT / "index.html").read_text()
faqs = [(f["q"], f["a"]) for f in cfg["faq"]]
page = between(page, "jsonld", ld({"@context": "https://schema.org", "@graph": [
    org(), {"@type": "WebSite", "@id": SITE + "/#site", "url": SITE + "/", "name": B["name"], "publisher": {"@id": SITE + "/#org"}},
    service(), faq_ld(faqs)]}))
page = between(page, "faq", "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faqs))
page = between(page, "plans", "".join(
    f'<div class="plan"><h3>{e(p["name"])}</h3><p class="per">{p["hours"]} hours · {e(p["total"])} in total</p>'
    f'<div class="price">${p["perHour"]}<small> /hour</small></div><ul>' + "".join(f"<li>{e(x)}</li>" for x in cfg["planFeatures"]) + "</ul></div>"
    for p in cfg["plans"]))
page = between(page, "tutors", "".join(
    f'<article class="fc"><h3>{e(t["name"])}</h3><p>{e(t["subject"])} tutor · {e(t["credentials"])}</p></article>' for t in cfg["tutors"]))
page = between(page, "regions", "".join(f'<li><a href="online-tutors-{r["slug"]}/">{e(r["label"])}</a></li>' for r in cfg["regions"]) + "<li>Worldwide</li>")
(ROOT / "index.html").write_text(page)

# ---- region pages --------------------------------------------------------------------------

STYLE = """:root{--ink:#0F3D3E;--ink-2:#4E5F5C;--paper:#F6F3E6;--card:#fff;--line:#DCE3D6;--olive:#5B6B32;--pale:#CBD69E;
--serif:"Bricolage Grotesque",system-ui,sans-serif;--sans:"Figtree",system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink-2);font:400 17px/1.6 var(--sans)}
a{color:var(--ink)}h1,h2,h3{font-family:var(--serif);color:var(--ink);letter-spacing:-.02em;line-height:1.1}
h1{font-size:clamp(34px,5vw,56px);margin:.3em 0}h2{font-size:clamp(24px,3vw,34px);margin:1.6em 0 .5em}
.wrap{max-width:860px;margin:0 auto;padding:0 20px}
header{display:flex;align-items:center;justify-content:space-between;padding:18px 20px;max-width:1100px;margin:0 auto}
.logo{display:flex;align-items:center;gap:10px;text-decoration:none;font:800 22px/1 var(--serif);color:var(--ink)}
.logo img{width:44px;height:44px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;background:var(--olive);color:#fff;text-decoration:none;
font:600 16px/1 var(--sans);padding:15px 22px;border-radius:999px}.btn.ghost{background:transparent;color:var(--ink);border:1.5px solid var(--ink)}
.eyebrow{font:700 13px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;color:var(--olive)}
.lead{font-size:20px}.ctas{display:flex;flex-wrap:wrap;gap:12px;margin:26px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:20px}
.card h3{margin:0 0 6px;font-size:20px}.price{font:800 40px/1 var(--serif);color:var(--ink)}
details{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 20px;margin-bottom:10px}
summary{font-weight:600;color:var(--ink);cursor:pointer}
footer{margin-top:64px;padding:32px 20px;border-top:1px solid var(--line);font-size:15px}
footer ul{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:8px 18px}"""


def region_page(r):
    url = f"{SITE}/online-tutors-{r['slug']}/"
    cities = ", ".join(r["cities"][:-1]) + " and " + r["cities"][-1]
    title = f"Online Tutors in {r['label']} · Expert 1:1 Tutoring, First Lesson Free · {B['name']}"
    desc = (f"Hand-picked 1:1 online tutors for students in {r['full']} ({', '.join(r['cities'][:3])}). "
            f"{r['curricula'][0].upper() + r['curricula'][1:]}, plus SAT, IMAT, BMAT and UCAT prep. From $10 an hour. First lesson free.")
    rfaq = [
        (f"Do you teach students in {r['full']}?",
         f"Yes. Every lesson is live and online, so students anywhere in {r['full']}, including {cities}, learn with the same hand-picked tutors."),
        (f"Which curriculums do you teach in {r['full']}?",
         f"We teach {r['curricula']}. We also prepare students for the SAT, IMAT, BMAT and UCAT."),
        ("What time are lessons?", f"Lessons are scheduled in {r['timezone']}, at times that suit your school day."),
        ("How much does online tutoring cost?",
         "Lessons cost $20 an hour on the 20-hour plan, $15 an hour on the 50-hour plan and $10 an hour on the 100-hour plan. "
         "Prices are in US dollars and are converted to your local currency at checkout. Your first lesson is free."),
        ("Is the first lesson really free?", "Yes. Your first lesson is free, with no payment details and no obligation."),
    ]
    graph = [org(), service(r), faq_ld(rfaq), {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": B["name"], "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": f"Online tutors in {r['label']}", "item": url}]}]
    others = "".join(f'<li><a href="../online-tutors-{o["slug"]}/">{e(o["label"])}</a></li>' for o in cfg["regions"] if o is not r)
    plans = "".join(f'<div class="card"><h3>{e(p["name"])}</h3><div class="price">${p["perHour"]}<small style="font-size:16px"> /hour</small></div>'
                    f'<p>{p["hours"]} hours · {e(p["total"])} in total{" · " + e(p["label"]) if p["label"] else ""}</p></div>' for p in cfg["plans"])
    tutors = "".join(f'<div class="card"><h3>{e(t["name"])}</h3><p>{e(t["subject"])} · {e(t["credentials"])}</p></div>' for t in cfg["tutors"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="website"><meta property="og:site_name" content="{e(B['name'])}">
<meta property="og:title" content="{e(f'Online tutors in {r["label"]} · {B["name"]}')}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{SITE}/assets/img/hero.webp">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0F3D3E">
<link rel="icon" type="image/svg+xml" href="../assets/logo/sas-emblem.svg"><link rel="icon" type="image/png" sizes="32x32" href="../assets/logo/favicon-32.png">
<link rel="apple-touch-icon" href="../assets/logo/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,800&family=Figtree:wght@400;600;700&display=swap" rel="stylesheet">
<style>{STYLE}</style>
{ld({"@context": "https://schema.org", "@graph": graph})}
</head>
<body>
<header><a class="logo" href="../"><img src="../assets/logo/sas-emblem.svg" alt="" width="44" height="44">SAS Tutors</a>
<a class="btn" href="../#top">Book a free trial</a></header>
<main class="wrap">
<span class="eyebrow">Online tutoring · {e(r['label'])}</span>
<h1>Expert 1:1 online tutors in {e(r['label'])}</h1>
<p class="lead">Hand-picked tutors for students in {e(cities)}. We teach {e(r['curricula'])}, plus SAT, IMAT, BMAT and UCAT prep. Live video lessons scheduled in {e(r['timezone'])}, and your first lesson is free.</p>
<div class="ctas"><a class="btn" href="../#top">Book your free trial</a><a class="btn ghost" href="{e(WA)}">Chat on WhatsApp</a></div>

<h2>Subjects we teach</h2>
<p>{e(', '.join(SUBJECTS[:-1]))} and {SUBJECTS[-1]}, from Years 4–12 to university courses.</p>

<h2>How it works</h2>
<div class="grid">
<div class="card"><h3>1. Tell us your goals</h3><p>Two minutes online or on WhatsApp: subject, level and the exam ahead.</p></div>
<div class="card"><h3>2. Meet your tutor</h3><p>We match a tutor to the curriculum, your child's level and your preferred times.</p></div>
<div class="card"><h3>3. See the progress</h3><p>Notes after every lesson and a written progress report every month.</p></div>
</div>

<h2>Prices</h2>
<div class="grid">{plans}</div>
<p>Prices are in US dollars and are converted to your local currency at checkout. Hours never expire and can be shared with family.</p>

<h2>Some of our tutors</h2>
<div class="grid">{tutors}</div>

<h2>Questions from families in {e(r['label'])}</h2>
{"".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in rfaq)}
<div class="ctas"><a class="btn" href="../#top">Book your free trial</a></div>
</main>
<footer><div class="wrap"><p>{e(B['about'])}</p><p><strong>We also teach students in</strong></p><ul>{others}</ul>
<p>© {datetime.date.today().year} {e(B['name'])} · <a href="../">sastutors.online</a></p></div></footer>
</body>
</html>
"""


for r in cfg["regions"]:
    d = ROOT / f"online-tutors-{r['slug']}"
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text(region_page(r))

# ---- sitemap, robots, llms.txt ------------------------------------------------------------

urls = [SITE + "/"] + [f"{SITE}/online-tutors-{r['slug']}/" for r in cfg["regions"]]
(ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
(ROOT / "robots.txt").write_text(
    "# Search engines and AI assistants are welcome to read and cite this site.\n"
    "User-agent: *\nAllow: /\nDisallow: /_logo/\nDisallow: /_video/\nDisallow: /_seo/\n\n"
    + "".join(f"User-agent: {bot}\nAllow: /\n\n" for bot in
              ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot",
               "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot"])
    + f"Sitemap: {SITE}/sitemap.xml\n")
plans_md = "\n".join(f"- {p['hours']} hours: ${p['perHour']}/hour (${p['hours'] * p['perHour']:,} total){' · ' + p['label'] if p['label'] else ''}" for p in cfg["plans"])
(ROOT / "llms.txt").write_text(f"""# {B['name']}

> {B['about']} Expert 1:1 online tutoring by live video with hand-picked tutors. 5,000+ hours of one-to-one lessons taught. The first lesson is free.

## Key facts
- Based in: the United Arab Emirates. All lessons are online, scheduled in the student's own timezone.
- Students in: {', '.join(r['label'] for r in cfg['regions'])}, and worldwide.
- Subjects: {', '.join(SUBJECTS)}.
- Curriculums: American (including AP), British (IGCSE, GCSE, O Level, A Level; AQA, Edexcel, OCR, Cambridge), IB, Indian (CBSE, ISC), Australian Years 4–12 (NAPLAN, HSC, VCE), university courses.
- Entry tests: SAT, IMAT, BMAT, UCAT.
- Contact: WhatsApp +{B['whatsapp']} · Instagram {B['instagramHandle']} · {SITE}/

## Prices (US dollars, converted to local currency at checkout)
{plans_md}
- First lesson free. Hours never expire, can be shared with family, and work for any subject, tutor or curriculum.

## Tutors
""" + "\n".join(f"- {t['name']}: {t['subject']}. {t['credentials']}" for t in cfg["tutors"]) + """

## Pages
- [Home]({site}/): overview, tutors, prices and FAQ
""".format(site=SITE) + "\n".join(f"- [Online tutors in {r['label']}]({SITE}/online-tutors-{r['slug']}/)" for r in cfg["regions"]) + """

## FAQ
""" + "\n".join(f"### {q}\n{a}\n" for q, a in faqs))
print(f"index.html, {len(cfg['regions'])} region pages, sitemap.xml, robots.txt, llms.txt")
