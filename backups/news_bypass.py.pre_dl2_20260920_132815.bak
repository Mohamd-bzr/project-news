#!/usr/bin/env python3
"""
News Bypass — advanced paywall reader, integrated into MOHMD NEWS
=================================================================
Ported from the user's tested bypass tool (bypass_news_enhanced.py)
and adapted for this project:

  * no hard cloudscraper dependency — used automatically when installed
  * returns the dict shape fetch_article_content() expects:
    {paragraphs, word_count, partial, title, url, resolved_url, site, method}
  * strategies, in order: direct (site config) → AMP versions →
    Googlebot UA fallback → Google Cache → (optional) cloudscraper
  * per-site configs for the 14 paywalled outlets from the original tool

Usage from the app:
    from news_bypass import smart_extract
    result = smart_extract(url, title, publisher)
"""

import json
import random
import re
import time
from urllib.parse import urlparse, quote_plus

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:                                    # optional — used when available
    import cloudscraper
except ImportError:
    cloudscraper = None


# ---------------------------------------------------------------------------
# user agents / referers / bypass cookies (from the original tool)
# ---------------------------------------------------------------------------

USER_AGENTS = {
    "googlebot_desktop": ("Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5 Build/MMB29P) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 "
                          "Mobile Safari/537.36 (compatible; Googlebot/2.1; "
                          "+http://www.google.com/bot.html)"),
    "googlebot_mobile": ("Mozilla/5.0 (Linux; Android 10; SM-G975U) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36 "
                         "(compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    "chrome_windows": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "chrome_mac": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "firefox_windows": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) "
                        "Gecko/20100101 Firefox/131.0"),
    "safari_mac": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                   "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"),
}

REFERERS = {
    "google": "https://www.google.com/",
    "google_amp": "https://www.google.com/amp/",
    "facebook": "https://www.facebook.com/",
    "twitter": "https://twitter.com/",
    "linkedin": "https://www.linkedin.com/",
    "bing": "https://www.bing.com/",
}

BYPASS_COOKIES = {
    "paywall_opt_out": "true",
    "paywall_disabled": "1",
    "premium_content_access": "true",
    "subscription_expiration": "null",
    "article_view_count": "1",
    "content_access_level": "free",
}

ENHANCED_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "DNT": "1",
    "Sec-GPC": "1",
}

# ---------------------------------------------------------------------------
# per-site configs (from the original tool, same shapes)
# ---------------------------------------------------------------------------

ENHANCED_SITE_CONFIGS = {
    "bloomberg.com": {
        "name": "Bloomberg",
        "useragent": "googlebot_desktop",
        "block_regex": [r"\.tinypass\.com/",
                        r"assets\.bwbx\.io/s\d+/(fence/plug-client|javelin/.+/transporter)/",
                        r"cdn\.amproject\.org/v\d+/amp-access-.*\.js",
                        r"\.premium\.(?:content|access)"],
        "allow_cookies": True,
        "remove_cookies_select_hold": ["bb_geo_info"],
        "add_bypass_cookies": True,
        "strategy": "multi",
        "xpath_extractors": [
            "//script[@data-component-props='ArticleBody']",
            "//script[@type='application/ld+json']",
            "//article//text()",
            "//div[@class='article-body']//text()"],
    },
    "wsj.com": {
        "name": "Wall Street Journal",
        "useragent": "googlebot_desktop",
        "block_regex": [r"cdn\.cxense\.com/",
                        r"cdn\.ampproject\.org/v\d+/amp-(access|subscriptions)-.+\.js",
                        r"meter-svc\.wsj\.com",
                        r"\.wsj\.com/paywall"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "amp_or_googlebot",
        "xpath_extractors": [
            "//script[@type='application/ld+json']",
            "//article[contains(@class,'article')]//text()",
            "//div[@id='article-body']//text()"],
    },
    "ft.com": {
        "name": "Financial Times",
        "useragent": "googlebot_desktop",
        "block_regex": [r"cdn\.ampproject\.org/v\d+/amp-access-.*\.js",
                        r"\.tinypass\.com/",
                        r"ft\.com/paywall"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "googlebot_with_amp",
        "xpath_extractors": [
            "//script[@type='application/ld+json']",
            "//article//text()",
            "//div[@class='article-body']//text()"],
    },
    "reuters.com": {
        "name": "Reuters",
        "useragent": "googlebot_desktop",
        "block_regex": [r"\.reuters\.com/(arc/subs/p\.min|pf/resources/dist/reuters/js/index)\.js",
                        r"reuters\.com/paywall"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "direct_with_js",
    },
    "nytimes.com": {
        "name": "New York Times",
        "useragent": "googlebot_desktop",
        "block_regex": [r"meter-svc\.nytimes\.com/meter\.js",
                        r"mwcm\.nyt\.com/.+\.js",
                        r"nytimes\.com/subscription"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "multi",
        "special_handlers": ["nytimes"],
    },
    "washingtonpost.com": {
        "name": "Washington Post",
        "useragent": "googlebot_desktop",
        "block_regex": [r"\.washingtonpost\.com/tetro/evaluate/",
                        r"wapo\.com/paywall"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "direct_with_amp",
    },
    "seekingalpha.com": {
        "name": "Seeking Alpha",
        "useragent": "googlebot_desktop",
        "block_regex": [r"cdn\.cxense\.com/",
                        r"\.tinypass\.com/",
                        r"cdn\.ampproject\.org/v\d+/amp-access-.*\.js",
                        r"seekingalpha\.com/paywall"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "amp_redirect",
        "special_handlers": ["seekingalpha"],
    },
    "businessinsider.com": {
        "name": "Business Insider",
        "useragent": "googlebot_desktop",
        "block_regex": [r"\.tinypass\.com/",
                        r"cdn\.ampproject\.org/v\d+/amp-access-.*\.js"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "googlebot_fallback",
    },
    "forbes.com": {
        "name": "Forbes",
        "useragent": "googlebot_desktop",
        "block_regex": [r"\.tinypass\.com/",
                        r"cdn\.ampproject\.org/v\d+/amp-access-.*\.js"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "multi",
    },
    "economist.com": {
        "name": "The Economist",
        "useragent": "googlebot_desktop",
        "block_regex": [r"\.tinypass\.com/",
                        r"cdn\.ampproject\.org/v\d+/amp-access-.*\.js"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "googlebot_fallback",
    },
    "cnbc.com": {
        "name": "CNBC",
        "useragent": "googlebot_desktop",
        "block_regex": [r"cnbc\.com/subscription"],
        "allow_cookies": True,
        "add_bypass_cookies": False,
        "strategy": "direct",
    },
    "finance.yahoo.com": {
        "name": "Yahoo Finance",
        "useragent": "googlebot_desktop",
        "block_regex": [r"yahoo\.com/paywall"],
        "allow_cookies": True,
        "add_bypass_cookies": False,
        "strategy": "direct",
    },
    "investing.com": {
        "name": "Investing.com",
        "useragent": "googlebot_desktop",
        "block_regex": [r"investing\.com/paywall"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "enhanced_googlebot",
        "xpath_extractors": [
            "//script[@type='application/ld+json']",
            "//article//text()",
            "//div[@class='article-content']//text()"],
    },
    "marketwatch.com": {
        "name": "MarketWatch",
        "useragent": "googlebot_desktop",
        "block_regex": [r"cdn\.cxense\.com/",
                        r"cdn\.ampproject\.org/v\d+/amp-access-.*\.js"],
        "allow_cookies": True,
        "add_bypass_cookies": True,
        "strategy": "amp_or_googlebot",
    },
}

PAYWALL_INDICATORS = [
    r"this content is for subscribers", r"please subscribe",
    r"register to read", r"you have reached your limit",
    r"content locked", r"paid content",
]
# strings that appear in normal pages too ("to continue reading" shows up in
# inline JS on free sites) — only checked OUTSIDE of script blocks
_SOFT_INDICATORS = [r"to continue reading", r"to view this content", r"sign up to continue"]


# ---------------------------------------------------------------------------
# reader
# ---------------------------------------------------------------------------

class EnhancedNewsBypassReader:
    """Ported reader — same strategy ladder as the tested original tool."""

    def __init__(self, debug=False):
        self.debug = debug
        self.session = self._create_session()
        self.scraper = cloudscraper.create_scraper() if cloudscraper else None

    # -- session ------------------------------------------------------------
    def _create_session(self):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.8,
                      status_forcelist=[429, 500, 502, 503, 504],
                      allowed_methods=["GET", "HEAD"])
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    # -- config / headers ---------------------------------------------------
    def _get_config(self, url):
        domain = urlparse(url).netloc.lower().replace("www.", "")
        for site, cfg in ENHANCED_SITE_CONFIGS.items():
            if domain == site or domain.endswith("." + site):
                cfg = dict(cfg)
                cfg["domain"] = site
                return site, cfg
        return domain, {
            "name": domain,
            "useragent": "chrome_windows",
            "block_regex": [],
            "allow_cookies": True,
            "add_bypass_cookies": False,
            "strategy": "enhanced_googlebot",
            "xpath_extractors": [
                "//script[@type='application/ld+json']",
                "//article//text()",
                "//div[@class='article-body']//text()"],
        }

    def _build_headers(self, config):
        headers = ENHANCED_HEADERS.copy()
        ua_key = config.get("useragent", "chrome_windows")
        headers["User-Agent"] = USER_AGENTS.get(ua_key, random.choice(list(USER_AGENTS.values())))
        if "googlebot" in ua_key:
            headers["X-Forwarded-For"] = "66.249.66.1"
        ref = config.get("referer")
        headers["Referer"] = REFERERS.get(ref, "https://www.google.com/")
        return headers

    def _build_cookies(self, config):
        cookies = {}
        if config.get("add_bypass_cookies"):
            cookies.update(BYPASS_COOKIES)
        for c in config.get("remove_cookies_select_hold", []):
            cookies[c] = "dummy"
        return cookies

    # -- paywall detection --------------------------------------------------
    def _is_paywall_blocked(self, content, config):
        if not content:
            return True
        # strip <script>/<style> first: inline JS on FREE sites is full of
        # phrases like "to continue reading" that false-trigger the ladder
        body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", content,
                      flags=re.S | re.I)
        low = body.lower()
        for pattern in config.get("block_regex", []):
            if re.search(pattern, low, re.I):
                return True
        for ind in PAYWALL_INDICATORS:
            if re.search(ind, low):
                return True
        name = config.get("name", "").lower()
        if name == "bloomberg" and ("fortress-paywall" in low or "article-body" not in content):
            return True
        if name == "new york times" and "meter-svc" in content:
            return True
        if name == "washington post" and "tetro/evaluate" in content:
            return True
        return False

    # -- AMP / cache urls ---------------------------------------------------
    def _amp_urls(self, url):
        parsed = urlparse(url)
        cands = [url.rstrip("/") + "/amp",
                 url.rstrip("/") + "?amp=1",
                 url.replace("www.", "amp.", 1),
                 f"https://amp.{parsed.netloc}{parsed.path}"]
        seen, out = set(), []
        for u in cands:
            if u.startswith("http") and u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _google_cache(self, url):
        return f"https://webcache.googleusercontent.com/search?q=cache:{url}&strip=1"

    # -- main ladder --------------------------------------------------------
    def read_article(self, url, max_retries=2):
        site, config = self._get_config(url)
        # CNBC/MarketWatch and friends hard-block the googlebot UA (403/401) but
        # serve plain Chrome fine; googlebot remains the paywall strategy for
        # FT/WSJ/Bloomberg-type sites only.
        if config.get("strategy") in ("direct", "direct_with_js", "amp_or_googlebot"):
            config = {**config, "useragent": "chrome_windows"}
        best = None

        def consider(method, title, text, extra=None):
            nonlocal best
            if text and len(text) > 200:
                cand = {"method": method, "title": title, "text": text,
                        "length": len(text)}
                if extra:
                    cand.update(extra)
                if best is None or cand["length"] > best["length"]:
                    best = cand
                return cand["length"] > 800      # good enough → stop ladder
            return False

        # 1) direct with site config
        try:
            headers = self._build_headers(config)
            resp = self.session.get(url, headers=headers,
                                    cookies=self._build_cookies(config),
                                    timeout=18, allow_redirects=True)
            if resp.status_code == 200 and not self._is_paywall_blocked(resp.text, config):
                title, text = self._extract_content_enhanced(resp.text, config, url)
                if consider(f"direct ({config.get('name')})", title, text,
                            {"resolved_url": resp.url}):
                    return self._package(best, url)
        except Exception:
            pass

        # 2) AMP versions
        for amp in self._amp_urls(url)[:3]:
            try:
                h = self._build_headers(config)
                h["User-Agent"] = USER_AGENTS["googlebot_mobile"]
                resp = self.session.get(amp, headers=h, timeout=15, allow_redirects=True)
                if resp.status_code == 200 and not self._is_paywall_blocked(resp.text, config):
                    title, text = self._extract_content_enhanced(resp.text, config, url)
                    if consider("amp_page", title, text, {"resolved_url": amp}):
                        return self._package(best, url)
            except Exception:
                continue

        # 3) googlebot fallback
        if config.get("strategy") != "googlebot_fallback":
            try:
                h = self._build_headers({**config, "useragent": "googlebot_desktop"})
                resp = self.session.get(url, headers=h, timeout=18, allow_redirects=True)
                if resp.status_code == 200 and not self._is_paywall_blocked(resp.text, config):
                    title, text = self._extract_content_enhanced(resp.text, config, url)
                    if consider("googlebot_fallback", title, text,
                                {"resolved_url": getattr(resp, "url", url)}):
                        return self._package(best, url)
            except Exception:
                pass

        # 4) google cache
        try:
            h = self._build_headers(config)
            resp = self.session.get(self._google_cache(url), headers=h,
                                    timeout=15, allow_redirects=True)
            if resp.status_code == 200 and not self._is_paywall_blocked(resp.text, config):
                title, text = self._extract_content_enhanced(resp.text, config, url)
                consider("google_cache", title, text)
        except Exception:
            pass

        # 5) cloudscraper (only when the package exists)
        if self.scraper is not None:
            try:
                h = self._build_headers(config)
                resp = self.scraper.get(url, headers=h, timeout=25, allow_redirects=True)
                if resp.status_code == 200 and not self._is_paywall_blocked(resp.text, config):
                    title, text = self._extract_content_enhanced(resp.text, config, url)
                    consider("cloudscraper", title, text, {"resolved_url": getattr(resp, "url", url)})
            except Exception:
                pass

        # 6) r.jina.ai reader — headless-browser rendering, no key needed;
        #    beats JS shells AND many paywalls in one hop
        try:
            r = self.session.get(f"https://r.jina.ai/{url}", timeout=45)
            if r.status_code == 200 and len(r.text) > 300:
                title, text = self._parse_reader_text(r.text)
                consider("jina-reader", title, text, {"resolved_url": url})
        except Exception:
            pass

        # 7) raw HTML proxies — the page fetched from someone else's IP
        for plabel, purl in (
                ("proxy-allorigins", f"https://api.allorigins.win/raw?url={quote_plus(url)}"),
                ("proxy-codetabs",   f"https://api.codetabs.com/v1/proxy?quest={quote_plus(url)}")):
            try:
                r = self.session.get(purl, timeout=30)
                if r.status_code == 200 and len(r.text) > 500 \
                        and not self._is_paywall_blocked(r.text, config):
                    title, text = self._extract_content_enhanced(r.text, config, url)
                    consider(plabel, title, text, {"resolved_url": url})
            except Exception:
                continue

        return self._package(best, url)

    # -- result shaping ------------------------------------------------------
    def _package(self, best, url):
        if not best:
            return {"paragraphs": [], "word_count": 0, "partial": True,
                    "title": "", "url": url, "resolved_url": None,
                    "bypass": "none"}
        text = self._clean_text_enhanced(best["text"])
        # kill leftover CSS/JS punctuation runs; keep real prose sentences only:
        # alpha ratio, no braces, no pseudo-class soup, mostly lowercase words
        _split_re = re.compile(r'(?<=[.!?؟])\s+(?=[A-Z"\u00ab\u201c(\'])')
        _CSS_NOISE = re.compile(
            r"(:{1,2}[\w-]+)|(\bnot\b)|(\bhover\b)|(\bfocus\b)|(\bsupports\b)|(\bdisabled\b)", re.I)
        _NAV_JUNK = re.compile(
            r"\b(livestream|watchlist|sign in|create free|search quotes|make it select"
            r"|menu|homepage|subscribe now|log ?in|skip to main content"
            r"|explore our brands|buy side|resizing|resize \()", re.I)
        paras = []
        for p in _split_re.split(text):
            p = p.strip()
            if len(p) < 40:
                continue
            alpha = sum(ch.isalpha() for ch in p)
            if alpha < len(p) * 0.62 or p.count("{") or _CSS_NOISE.search(p[:120]):
                continue
            if _NAV_JUNK.search(p[:90]):
                continue          # site chrome: nav/CTA fragments anywhere in the lead
            paras.append(p)
        if not paras and text and sum(ch.isalpha() for ch in text) > len(text) * 0.62 \
                and not _CSS_NOISE.search(text[:120]):
            paras = [text]
        return {"paragraphs": paras[:150],
                "word_count": sum(len(p.split()) for p in paras),
                "partial": sum(len(p.split()) for p in paras) < 120,
                "title": best.get("title", ""),
                "url": url,
                "resolved_url": best.get("resolved_url"),
                "bypass": best.get("method", "")}

    # -- extraction ----------------------------------------------------------
    def _extract_content_enhanced(self, html, config, original_url=""):
        title, text = "", ""

        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        for handler in config.get("special_handlers", []):
            if handler == "nytimes":
                title, text = self._extract_nytimes_content(html)
                if text and len(text) > 100:
                    return title, text
            elif handler == "seekingalpha":
                title, text = self._extract_seekingalpha_content(html, original_url)
                if text and len(text) > 100:
                    return title, text

        # 1) inline JSON blocks (bloomberg-style)
        for pat in (r'<script[^>]*data-component-props="ArticleBody"[^>]*>(.*?)</script>',
                    r'<script[^>]*id="article-body"[^>]*>(.*?)</script>'):
            m = re.search(pat, html, re.S | re.I)
            if m:
                got = self._extract_from_json_enhanced(m.group(1))
                if got["text"] and len(got["text"]) > 200:
                    title = title or got["title"]
                    text = got["text"]
                    break

        # 2) schema.org ld+json
        if not text or len(text) < 200:
            for lm in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                                  html, re.S):
                try:
                    ld = json.loads(lm.group(1))
                except json.JSONDecodeError:
                    continue
                stack = ld if isinstance(ld, list) else [ld]
                for node in stack:
                    got = self._extract_from_ld_json_enhanced(node)
                    if len(got.get("text", "")) > len(text):
                        text = got["text"]
                        title = title or got["title"]

        # 3) DOM containers — take the <p> TEXT inside the container, not the
        #    container's raw innerHTML: MarketWatch-style pages open the article
        #    div with a wall of CSS pseudo-classes that poisons tag-stripping.
        if not text or len(text) < 200:
            stripped = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html,
                              flags=re.S | re.I)
            containers = []
            for sel in (r'<div[^>]*class="[^"]*article-body[^"]*"[^>]*>(.*)',
                        r'<article[^>]*>(.*?)</article>',
                        r'<div[^>]*class="[^"]*article-content[^"]*"[^>]*>(.*?)</div>',
                        r'<div[^>]*class="[^"]*story-body[^"]*"[^>]*>(.*?)</div>',
                        r'<div[^>]*class="[^"]*post-content[^"]*"[^>]*>(.*?)</div>'):
                m = re.search(sel, stripped, re.S | re.I)
                if m:
                    containers.append(m.group(1)[:60000])
            for body in containers:
                ps = [" ".join(re.sub(r"<[^>]+>", " ", p).split())
                      for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S | re.I)]
                long_ps = [p for p in ps if len(p) > 100]
                if long_ps:
                    t = self._clean_text_enhanced(" ".join(long_ps))
                    if len(t) > len(text or ""):
                        text = t
            # classic tag-strip as the second chance
            if not text:
                for sel in (r'<article[^>]*>(.*?)</article>',
                            r'<div[^>]*class="[^"]*article-body[^"]*"[^>]*>(.*?)</div>',
                            r'<div[^>]*class="[^"]*story-body[^"]*"[^>]*>(.*?)</div>'):
                    m = re.search(sel, stripped, re.S | re.I)
                    if m:
                        t = re.sub(r"<[^>]+>", " ", m.group(1))
                        t = self._clean_text_enhanced(t)
                        if len(t) > 200:
                            text = t
                            break

        # 4) all <p> as last resort
        if not text or len(text) < 200:
            ps = re.findall(r"<p[^>]*>(.*?)</p>", html, re.S | re.I)
            joined = self._clean_text_enhanced(
                " ".join(re.sub(r"<[^>]+>", " ", p) for p in ps))
            if len(joined) > 300:
                text = joined

        return title, text

    def _extract_from_json_enhanced(self, raw):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"title": "", "text": ""}
        paths = [("body", "nodes"), ("articleBody",), ("content", "body"),
                 ("article", "content"), ("blocks",), ("paragraphs",),
                 ("text",), ("body", "text"), ("sections",)]
        for path in paths:
            cur = data
            try:
                for key in path:
                    cur = cur[key] if not isinstance(cur, list) else cur[0][key]
                if isinstance(cur, str):
                    t = self._clean_text_enhanced(re.sub(r"<[^>]+>", " ", cur))
                    return {"title": data.get("headline", data.get("title", "")), "text": t}
                if isinstance(cur, (dict, list)):
                    parts = []
                    self._walk(cur, parts)
                    t = self._clean_text_enhanced(" ".join(parts))
                    return {"title": data.get("headline", data.get("title", "")), "text": t}
            except (KeyError, TypeError, IndexError):
                continue
        return {"title": "", "text": ""}

    def _walk(self, obj, parts):
        if isinstance(obj, str):
            parts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                self._walk(v, parts)
        elif isinstance(obj, list):
            for it in obj:
                self._walk(it, parts)

    def _extract_from_ld_json_enhanced(self, ld):
        if not isinstance(ld, dict):
            return {"title": "", "text": ""}
        title = ld.get("headline", ld.get("name", ""))
        for f in ("articleBody", "description", "text", "abstract", "content"):
            v = ld.get(f)
            if isinstance(v, str):
                t = self._clean_text_enhanced(v)
                if len(t) > 100:
                    return {"title": title, "text": t}
            elif isinstance(v, list):
                t = self._clean_text_enhanced(
                    " ".join(str(x) for x in v if isinstance(x, str)))
                if len(t) > 100:
                    return {"title": title, "text": t}
        return {"title": "", "text": ""}

    def _parse_reader_text(self, text):
        """Parse r.jina.ai output: 'Title: …' header + 'Markdown Content:' body."""
        title = ""
        body = text
        m = re.search(r"^Title:\s*(.+)$", text, re.M)
        if m:
            title = m.group(1).strip()
        m = re.search(r"^Markdown Content:\s*$", text, re.M)
        if m:
            body = text[m.end():]
        lines = []
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith(("#", "![", "[!", ">", "---", "|", "```")):
                continue
            ln = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", ln)
            ln = re.sub(r"[*_`]{1,3}", "", ln)
            if len(ln) < 55:
                continue
            lines.append(ln)
        return title, " ".join(lines)

    def _clean_text_enhanced(self, text):
        if not text:
            return ""
        # CSS-in-JS fragments (.css-xxxx{...}) leak from MarketWatch-type pages;
        # they are long, punctuation-heavy and not prose — drop every run of them
        text = re.sub(r"[\w.@:;#-]*\{[^{}]*\}", " ", text)
        text = re.sub(r"[\w.@:;#-]*\{[^{}]*\}", " ", text)   # nested pass
        text = re.sub(r"\.css-[\w-]+|\.Mui[\w-]+|fontMetrics|@media[^{]*", " ", text)
        text = re.sub(r"[{};]", " ", text)
        text = re.sub(r"\s+", " ", text)
        junk = (r"footer|navigation|menu|sidebar|aside|related articles|"
                r"share this article|comments|login to comment|register|"
                r"subscribe|advertisement|advertising|sponsored content|related posts|"
                r"you are being redirected|access denied|please enable javascript|"
                r"javascript required|content is loading|loading content|please wait|"
                r"error loading|unable to load|this is a premium article|"
                r"premium content|subscription required|registration required|"
                r"please login|login to continue|sign up to continue|"
                r"create an account|follow this author|follow for more")
        text = re.sub(junk, "", text, flags=re.I)
        return text.strip()


# ---------------------------------------------------------------------------
# public API used by app.py — smart_extract(url)
# ---------------------------------------------------------------------------

_READER = None
_RES_CACHE = {}          # url -> (fetched_at, result)
_RES_TTL_OK = 6 * 3600   # full extractions are solid — cache 6 h
_RES_TTL_FAIL = 10 * 60  # failures/partial are retried after 10 min
def _reader():
    global _READER
    if _READER is None:
        _READER = EnhancedNewsBypassReader()
    return _READER


def web_extract(urls):
    """Compatibility helper: [{url, title, content}] per URL."""
    out = []
    for u in urls:
        r = smart_extract(u)
        out.append({"url": u, "title": r.get("title", ""),
                    "content": "\n\n".join(r.get("paragraphs", []))})
    return out


def smart_extract(url, title="", publisher=""):
    """Try the plain extractor first is the CALLER's job — this function is the
    paywall fallback. Results are cached with a TTL: thin/failed extractions
    expire quickly so a one-off network blip never sticks forever."""
    ent = _RES_CACHE.get(url)
    if ent:
        ts, res = ent
        if time.time() - ts < (_RES_TTL_OK if res.get("paragraphs") else _RES_TTL_FAIL):
            return res
    try:
        res = _reader().read_article(url)
    except Exception:
        res = {"paragraphs": [], "word_count": 0, "partial": True,
               "title": "", "url": url, "resolved_url": None}
    _RES_CACHE[url] = (time.time(), res)
    if len(_RES_CACHE) > 400:
        _RES_CACHE.pop(next(iter(_RES_CACHE)))
    return res


if __name__ == "__main__":
    import sys
    u = sys.argv[1] if len(sys.argv) > 1 else \
        "https://www.investing.com/news/economy-news/analysisfed-builds-credibility-but-hawkish-turn-leaves-investors-edgy-4904805"
    r = smart_extract(u)
    print("method :", r.get("bypass"))
    print("title  :", (r.get("title") or "")[:90])
    print("words  :", r.get("word_count"), " partial:", r.get("partial"))
    for p in r.get("paragraphs", [])[:3]:
        print("  ¶", p[:130])
