"""Сборка сайта OneDPI: python build.py -> dist/

Страницы лежат в src/pages/*.html (только содержимое <main>), версии в src/versions.json,
статьи вики в src/wiki/*.md. Порядок и группы вики задаёт WIKI ниже.
"""

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
CHANNEL = "https://t.me/OneDPI"
REPO = "https://github.com/Wandraker/onedpi-site"
APK = f"{REPO}/releases/latest/download/OneDPI.apk"
# Платный VPN той же команды. Когда появится бот, заменить на ссылку t.me/<бот>.
BYEVPN = "https://byevpn.byevpn.workers.dev/"
RELEASE = json.loads((Path(__file__).resolve().parent / "src" / "release.json").read_text(encoding="utf-8"))
SITE = "https://wandraker.github.io/onedpi-site/"
FONTS = "https://fonts.googleapis.com/css2?family=Geologica:wght@300..700&family=Tektur:wdth,wght@75..100,400..900&display=swap"

WIKI = [
    ("start", "Начало", "flag", ["index", "install", "first-run", "statuses"]),
    ("inside", "Как это работает", "split", ["how-it-works", "smart", "profiles", "diagnostics"]),
    ("trouble", "Если что-то не так", "wrench", ["sites", "telegram", "exclusions", "update"]),
    ("devices", "Устройства", "tv", ["android-tv"]),
    ("more", "Ещё", "dots", ["privacy", "faq"]),
]

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]

_I = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{}</svg>'
ICONS = {
    "flag": _I.format('<path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/>'),
    "split": _I.format('<rect x="4" y="5" width="6" height="12" rx="1.5"/><rect x="14" y="8" width="6" height="12" rx="1.5"/>'),
    "wrench": _I.format('<path d="M14.5 6.5a4 4 0 0 0-5.3 5.3L4 17l3 3 5.2-5.2a4 4 0 0 0 5.3-5.3l-2.6 2.6-2.4-.6-.6-2.4z"/>'),
    "tv": _I.format('<rect x="3" y="5" width="18" height="12" rx="2"/><path d="M8 21h8"/>'),
    "dots": _I.format('<circle cx="6" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18" cy="12" r="1.2"/>'),
    "search": _I.format('<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>'),
    "menu": _I.format('<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h10"/>'),
    "close": _I.format('<path d="M6 6l12 12"/><path d="M18 6 6 18"/>'),
}


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def inline(s: str) -> str:
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.U)
    return re.sub(r"\s+", "-", s.strip())


def markdown(text: str) -> str:
    out, para, items, kind = [], [], [], None

    def flush():
        nonlocal para, items, kind
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para = []
        if items:
            tag = "ol" if kind == "ol" else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{tag}>")
            items, kind = [], None

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush()
            continue
        if s.startswith("## "):
            flush()
            title = s[3:]
            out.append(f'<h2 id="{slugify(title)}">{inline(title)}</h2>')
        elif s.startswith("### "):
            flush()
            out.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith("> "):
            flush()
            out.append(f'<p class="note">{inline(s[2:])}</p>')
        elif re.match(r"^- ", s):
            if para or kind == "ol":
                flush()
            kind = "ul"
            items.append(s[2:])
        elif re.match(r"^\d+\. ", s):
            if para or kind == "ul":
                flush()
            kind = "ol"
            items.append(re.sub(r"^\d+\. ", "", s))
        else:
            if items:
                flush()
            para.append(s)
    flush()
    return "\n".join(out)


def read_article(slug: str) -> dict:
    raw = (SRC / "wiki" / f"{slug}.md").read_text(encoding="utf-8").replace("{{byevpn}}", BYEVPN)
    _, front, body = raw.split("---", 2)
    meta = {}
    for line in front.strip().splitlines():
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
    meta["slug"] = slug
    meta["html"] = markdown(body)
    meta["text"] = re.sub(r"\s+", " ", re.sub(r"[#>*`\[\]()-]", " ", body)).strip()
    return meta


def nice_date(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS[m - 1]} {y}"


def version_item(v: dict) -> str:
    cls = f' class="{v["kind"]}"' if v.get("kind") else ""
    tags = ""
    if v.get("tag"):
        tags += f'<span class="tag">{esc(v["tag"])}</span>'
    if v.get("date"):
        tags += f'<time class="tag" datetime="{v["date"]}">{nice_date(v["date"])}</time>'
    return (f'<li{cls}><div class="ver"><span class="ver-num">{esc(v["num"])}</span>'
            f'<span class="ver-title">{esc(v["title"])}</span>{tags}</div><p>{esc(v["text"])}</p></li>')


def versions_latest(versions: list, root: str) -> str:
    shown = [v for v in versions if v.get("kind") != "pause"][-4:]
    items = "".join(version_item(v) for v in shown)
    return f"""<section class="section" id="versions">
    <div class="wrap">
      <div class="section-head">
        <h2>Как растёт приложение</h2>
        <p>Последние версии. Сверху — то, что сейчас, ниже — что было до.</p>
      </div>
      <ol class="timeline timeline-short">{items}</ol>
      <a class="more-link" href="{root}versions.html">Все версии, с самой первой</a>
    </div>
  </section>"""


def versions_all(versions: list) -> str:
    items = "".join(version_item(v) for v in versions)
    return f"""<section class="section">
    <div class="wrap">
      <div class="section-head">
        <h1 class="page-title">Все версии</h1>
        <p>Каждая версия выходила после отзывов тестировщиков из России и Казахстана. Сверху — то, что сейчас, внизу — самое начало.</p>
      </div>
      <ol class="timeline">{items}</ol>
    </div>
  </section>"""


def wiki_sidebar(articles: dict, current: str) -> str:
    groups = []
    for _, label, icon, slugs in WIKI:
        links = []
        for slug in slugs:
            a = articles[slug]
            href = "./" if slug == "index" else f"{slug}.html"
            cur = ' aria-current="page"' if slug == current else ""
            links.append(f'<a href="{href}"{cur} data-wiki-link data-slug="{slug}">{esc(a["title"])}</a>')
        groups.append(f'<div class="wiki-group" data-wiki-group><p class="wiki-group-title">{ICONS[icon]}{label}</p>{"".join(links)}</div>')
    return f"""<aside class="wiki-side">
  <details class="wiki-side-toggle" data-wiki-toggle open>
    <summary>Разделы вики</summary>
    <label class="wiki-search">{ICONS["search"]}<input type="search" placeholder="Поиск" aria-label="Поиск по вики" data-wiki-search><kbd>Ctrl K</kbd></label>
    <nav aria-label="Разделы вики">{"".join(groups)}<p class="wiki-empty" data-wiki-empty hidden>Ничего не нашлось</p></nav>
  </details>
</aside>"""


def wiki_cards(articles: dict) -> str:
    out = []
    for _, label, icon, slugs in WIKI:
        cards = "".join(
            f'<a class="wiki-card" href="{s}.html"><span class="wiki-card-title">{esc(articles[s]["title"])}</span>'
            f'<span class="wiki-card-hint">{esc(articles[s]["hint"])}</span></a>'
            for s in slugs if s != "index")
        out.append(f'<section class="wiki-section"><h2 class="wiki-section-title">{ICONS[icon]}{label}</h2><div class="wiki-cards">{cards}</div></section>')
    return "\n".join(out)


def wiki_page(articles: dict, order: list, slug: str) -> str:
    a = articles[slug]
    i = order.index(slug)
    pager = ""
    if i > 0:
        p = articles[order[i - 1]]
        href = "./" if p["slug"] == "index" else f'{p["slug"]}.html'
        pager += f'<a class="prev" href="{href}"><span>Назад</span>{esc(p["title"])}</a>'
    if i < len(order) - 1:
        n = articles[order[i + 1]]
        pager += f'<a class="next" href="{n["slug"]}.html"><span>Далее</span>{esc(n["title"])}</a>'
    body = wiki_cards(articles) if slug == "index" else a["html"]
    toc = "" if slug == "index" else '<aside class="wiki-toc" aria-label="На этой странице"><p class="wiki-toc-title">На этой странице</p><nav data-wiki-toc></nav></aside>'
    return f"""<div class="wrap wiki-grid{' wiki-home' if slug == 'index' else ''}">
{wiki_sidebar(articles, slug)}
<article class="wiki-content" data-wiki-article>
  <header class="wiki-head"><h1>{esc(a["title"])}</h1><p class="lead">{inline(a["lead"])}</p></header>
  {body}
  <nav class="wiki-pager" aria-label="Соседние статьи">{pager}</nav>
</article>
{toc}
</div>"""


def page(body: str, title: str, desc: str, root: str, current: str) -> str:
    def nav_link(key, href, label):
        cur = ' aria-current="page"' if key == current else ""
        return f'<a href="{href}"{cur}>{label}</a>'

    nav = "".join([
        nav_link("index", f"{root}./", "Главная"),
        nav_link("how", f"{root}./#how", "Как работает"),
        nav_link("wiki", f"{root}wiki/", "Вики"),
        nav_link("versions", f"{root}versions.html", "Все версии"),
        f'<a href="{CHANNEL}">Telegram-канал</a>',
    ])
    full_title = title if title == "OneDPI" else f"{title} · OneDPI"
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(full_title)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="theme-color" content="#17133A">
  <meta property="og:title" content="{esc(full_title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:image" content="{SITE}assets/og.png">
  <link rel="icon" href="{root}assets/icon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="{FONTS}">
  <link rel="stylesheet" href="{root}assets/site.css">
  <script>try{{var t=localStorage.getItem("onedpi-theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body data-root="{root}">
<a class="skip" href="#main">К содержимому</a>

<header class="site-head">
  <div class="wrap">
    <a class="brand" href="{root}./"><img src="{root}assets/icon.svg" alt="" width="32" height="32">OneDPI</a>
    <div class="head-actions">
      <a class="head-cta" href="{APK}">Скачать</a>
      <button class="menu-btn" type="button" aria-haspopup="dialog" aria-controls="drawer" data-menu-open>{ICONS["menu"]}<span>Меню</span></button>
    </div>
  </div>
</header>

<dialog class="drawer" id="drawer" aria-label="Меню">
  <div class="drawer-head">
    <span class="drawer-title">OneDPI</span>
    <button class="menu-btn" type="button" data-menu-close>{ICONS["close"]}<span>Закрыть</span></button>
  </div>
  <nav class="drawer-nav" aria-label="Разделы сайта">{nav}</nav>
  <div class="drawer-foot">
    <button class="theme-toggle" type="button" data-theme-toggle>Сменить тему</button>
  </div>
</dialog>

<main id="main">
{body}
</main>

<footer class="site-foot">
  <div class="wrap">
    <div>
      <h3>OneDPI</h3>
      <p>© 2026 Wandraker (Onelsey). Все права защищены. Тексты, дизайн, логотип и скриншоты нельзя копировать без разрешения.</p>
      <p>Независимый проект. Не связан с командой ByeByeDPI.</p>
    </div>
    <div>
      <h3>Внутри работают</h3>
      <p><a href="https://github.com/hufrea/byedpi">ByeDPI</a> от hufrea, MIT.</p>
      <p><a href="https://github.com/heiher/hev-socks5-tunnel">hev-socks5-tunnel</a> от heiher, MIT.</p>
      <p>WireGuard для Android, Apache 2.0.</p>
    </div>
    <div>
      <h3>Разделы</h3>
      <p><a href="{root}wiki/">Вики</a></p>
      <p><a href="{root}versions.html">Все версии</a></p>
      <p><a href="{CHANNEL}">Telegram-канал</a> — релизы и новости.</p>
    </div>
  </div>
</footer>

<script src="{root}assets/site.js"></script>
</body>
</html>
"""


SITE_ROOT = "/onedpi-site/"


def not_found_page(root: str) -> str:
    return f"""<section class="section notfound">
  <div class="wrap">
    <p class="notfound-code" aria-hidden="true">404</p>
    <h1>Такой страницы нет</h1>
    <p class="lede">Возможно, она была удалена или переименована, а ссылка устарела. Либо в адресе опечатка.</p>
    <ul class="notfound-links">
      <li><a class="button" href="{root}">На главную</a></li>
      <li><a href="{root}wiki/">Вики: ответы на частые вопросы</a></li>
      <li><a href="{root}versions.html">Все версии</a></li>
      <li><a href="{CHANNEL}">Спросить в Telegram-канале</a></li>
    </ul>
  </div>
</section>"""


def moved_page(target: str, label: str) -> str:
    return f"""<section class="section notfound">
  <div class="wrap">
    <h1>Страница переехала</h1>
    <p class="lede">Этого раздела здесь больше нет. То, что в нём было, теперь в разделе «{label}».</p>
    <ul class="notfound-links">
      <li><a class="button" href="{target}">Открыть «{label}»</a></li>
      <li><a href="./">На главную</a></li>
    </ul>
  </div>
</section>"""


def redirect(target: str) -> str:
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>OneDPI</title>
<meta http-equiv="refresh" content="0; url={target}"><link rel="canonical" href="{target}">
<script>location.replace("{target}" + location.hash)</script></head>
<body><a href="{target}">{target}</a></body></html>
"""


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "wiki").mkdir(parents=True)
    shutil.copytree(ROOT / "assets", DIST / "assets")

    versions = json.loads((SRC / "versions.json").read_text(encoding="utf-8"))

    home = (SRC / "pages" / "index.html").read_text(encoding="utf-8")
    home = home.replace("{{byevpn}}", BYEVPN).replace("{{versions_latest}}", versions_latest(versions, "")).replace("{{root}}", "")
    home = (home.replace("{{apk}}", APK).replace("{{apk_version}}", RELEASE["version"])
            .replace("{{apk_size}}", RELEASE["size"]).replace("{{apk_sha}}", RELEASE["sha256"])
            .replace("{{release_page}}", f'{REPO}/releases/tag/{RELEASE["tag"]}'))
    (DIST / "index.html").write_text(page(home, "OneDPI",
        "OneDPI — Android-приложение, которое обходит DPI-блокировки прямо на телефоне. Без сервера, без аккаунта, одной кнопкой.",
        "", "index"), encoding="utf-8")
    (DIST / "versions.html").write_text(page(versions_all(versions), "Все версии",
        "История OneDPI от первой сборки до текущей версии.", "", "versions"), encoding="utf-8")

    order = [s for _, _, _, slugs in WIKI for s in slugs]
    articles = {s: read_article(s) for s in order}
    search = {}
    for slug in order:
        a = articles[slug]
        name = "index.html" if slug == "index" else f"{slug}.html"
        title = "Вики" if slug == "index" else f'{a["title"]} · Вики'
        (DIST / "wiki" / name).write_text(page(wiki_page(articles, order, slug), title, a["hint"], "../", "wiki"), encoding="utf-8")
        search[slug] = f'{a["title"]} {a["hint"]} {a.get("keywords", "")} {a["text"]}'.lower()
    (DIST / "wiki" / "search.json").write_text(json.dumps(search, ensure_ascii=False), encoding="utf-8")

    # GitHub Pages serves 404.html for any unknown address at any depth, so links are absolute.
    (DIST / "404.html").write_text(page(not_found_page(SITE_ROOT), "Страница не найдена",
        "Такой страницы на сайте OneDPI нет.", SITE_ROOT, "404"), encoding="utf-8")
    # The old help page moved to the wiki: say so instead of silently jumping there.
    (DIST / "help.html").write_text(page(moved_page("wiki/", "Вики"), "Страница переехала",
        "Справка OneDPI теперь в вики.", "", "moved"), encoding="utf-8")
    shutil.copy(ROOT / "LICENSE", DIST / "LICENSE")
    (DIST / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {len(order)} wiki pages, {len(versions)} versions -> {DIST}")


if __name__ == "__main__":
    main()
