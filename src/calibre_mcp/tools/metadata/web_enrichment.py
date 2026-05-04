"""
Web metadata enrichment tools for CalibreMCP.

Fetches raw page text from online sources (Wikipedia, 萌娘百科, wenku8.net).
Returns the text to the LLM for natural-language metadata extraction.

This is more robust than regex-based HTML parsing because:
- LLM understands context and can handle varied page structures
- No fragile regex patterns to maintain
- Handles edge cases naturally
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ...logging_config import get_logger
from ...server import mcp

logger = get_logger("calibremcp.tools.metadata")

# ── Wikipedia API ──────────────────────────────────────────────────────────

WIKIPEDIA_API_JA = "https://ja.wikipedia.org/w/api.php"
WIKIPEDIA_API_ZH = "https://zh.wikipedia.org/w/api.php"
WIKIPEDIA_UA = "CalibreMCP/1.0 (metadata enrichment tool)"


def _wiki_api_call(api_url: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Make a request to Wikipedia API and return parsed JSON."""
    params["format"] = "json"
    params["utf8"] = "1"
    url = f"{api_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": WIKIPEDIA_UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning(f"Wikipedia API error: {e}")
        return None


def _fetch_wikipedia_extract(title: str) -> dict[str, Any]:
    """
    Fetch Wikipedia article extract (plain text) for a book title.

    Searches Japanese Wikipedia first, then Chinese Wikipedia.
    Returns the extract text and page metadata.
    """
    result: dict[str, Any] = {"source": "wikipedia", "found": False}

    for api_url, lang in [(WIKIPEDIA_API_JA, "ja"), (WIKIPEDIA_API_ZH, "zh")]:
        # Search
        search_data = _wiki_api_call(api_url, {
            "action": "query",
            "list": "search",
            "srsearch": title,
            "srlimit": "3",
        })
        if not search_data:
            continue
        pages = search_data.get("query", {}).get("search", [])
        if not pages:
            continue

        # Skip disambiguation pages
        page_title = None
        for p in pages:
            t = p.get("title", "")
            if not ("(" in t and "曖昧さ回避" in t):
                page_title = t
                break
        if not page_title:
            page_title = pages[0].get("title", "")

        result["page_title"] = page_title
        result["lang"] = lang
        result["url"] = (
            f"https://{'ja' if lang == 'ja' else 'zh'}.wikipedia.org/wiki/"
            + urllib.parse.quote(page_title)
        )

        # Fetch extract
        extract_data = _wiki_api_call(api_url, {
            "action": "query",
            "titles": page_title,
            "prop": "extracts",
            "exintro": "1",
            "explaintext": "1",
        })
        if extract_data:
            for _pid, pdata in extract_data.get("query", {}).get("pages", {}).items():
                if _pid != "-1" and pdata.get("extract"):
                    result["found"] = True
                    result["text"] = pdata["extract"].strip()
                    return result

    return result


# ── curl_cffi helper ──────────────────────────────────────────────────────
# curl_cffi impersonates browser TLS fingerprints to bypass Cloudflare.
# Each site needs a specific browser fingerprint.

CURL_AVAILABLE = False
try:
    from curl_cffi import requests as curl_requests  # noqa: F401

    CURL_AVAILABLE = True
except ImportError:
    pass


def _curl_get(
    url: str,
    impersonate: str = "chrome131_android",
    cookie: str | None = None,
    headers: dict[str, str] | None = None,
    encoding: str | None = None,
) -> str | None:
    """
    Fetch a URL using curl_cffi with browser TLS impersonation.

    Args:
        url: Target URL
        impersonate: Browser fingerprint to use (e.g. "chrome131_android", "chrome146")
        cookie: Optional Cookie header string
        headers: Additional headers
        encoding: Manual encoding override (e.g. "gbk" for wenku8).
                  If None, auto-detects from Content-Type, falls back to utf-8.

    Returns:
        Response text on success, None on failure
    """
    if not CURL_AVAILABLE:
        logger.warning("curl_cffi not installed — cannot fetch Cloudflare-protected sites")
        return None

    from curl_cffi import requests

    try:
        s = requests.Session()
        s.impersonate = impersonate
        s.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
        })
        if cookie:
            s.headers["Cookie"] = cookie
        if headers:
            s.headers.update(headers)

        resp = s.get(url, timeout=30)
        if resp.status_code != 200:
            logger.debug(f"curl_cffi HTTP {resp.status_code} for {url}")
            return None

        # Decode with correct encoding
        raw = resp.content  # bytes — avoid curl_cffi's auto-decoding
        if encoding:
            return raw.decode(encoding, errors="replace")

        # Auto-detect from Content-Type charset
        ct = resp.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w-]+)", ct, re.IGNORECASE)
        detected = m.group(1).lower() if m else None
        if detected and detected != "utf-8":
            return raw.decode(detected, errors="replace")
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning(f"curl_cffi error for {url}: {e}")
        return None


# ── HTML → Plain text ────────────────────────────────────────────────────


def _html_to_text(html_content: str) -> str:
    """
    Convert HTML to readable plain text.

    Strips tags, decodes entities, removes scripts/styles,
    and normalizes whitespace.
    """
    import html as html_mod

    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)

    # Replace block-level tags with newlines
    for tag in ["p", "br", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"]:
        text = re.sub(rf"</?{tag}[^>]*>", "\n", text)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html_mod.unescape(text)

    # Clean up: remove reference markers, normalize whitespace
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


# ── 萌娘百科 ──────────────────────────────────────────────────────────────

MOEGIRL_URL = "https://zh.moegirl.org.cn"


def _fetch_moegirl_text(title: str, cookie: str | None = None) -> dict[str, Any]:
    """
    Fetch 萌娘百科 page text for a book title.

    Requires curl_cffi with a desktop Chrome fingerprint (chrome146).
    Returns the page text and basic metadata.
    """
    result: dict[str, Any] = {"source": "moegirl", "found": False}

    encoded = urllib.parse.quote(title)
    url = f"{MOEGIRL_URL}/{encoded}"

    html_content = _curl_get(
        url,
        impersonate="chrome146",
        cookie=cookie,
        headers={
            "Referer": f"{MOEGIRL_URL}/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            ),
        },
    )
    if not html_content:
        return result

    result["url"] = url
    result["found"] = True

    # Extract the main article content (between mw-content-text and its end)
    # This gives us focused text instead of the entire page
    main_match = re.search(
        r'class="mw-content-text[^"]*">(.*?)<div\s+(?:class|id)="(?:printfooter|mw-panel|catlinks)',
        html_content,
        re.DOTALL,
    )
    text_source = main_match.group(1) if main_match else html_content
    result["text"] = _html_to_text(text_source)

    # Also try to get the page title
    title_match = re.search(r"<title>(.*?)</title>", html_content)
    if title_match:
        result["page_title"] = title_match.group(1).split(" - ")[0].strip()

    return result


# ── wenku8 轻小说文库 ──────────────────────────────────────────────────────

WENKU8_SEARCH_URL = "https://www.wenku8.net/modules/article/search.php"
WENKU8_BOOK_URL = "https://www.wenku8.net/book/{}.htm"
WENKU8_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "wenku8_headers.json"
)


def _load_wenku8_config() -> dict[str, Any] | None:
    """
    Load the saved browser headers config for wenku8.net.

    Reads from config/wenku8_headers.json which stores the User-Agent,
    Cookie (with cf_clearance), and browser fingerprint parameters
    extracted from Chrome DevTools.

    Returns the full config dict, or None if the file doesn't exist.
    """
    try:
        if WENKU8_CONFIG_PATH.exists():
            with open(WENKU8_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load wenku8 config: {e}")
    return None


def _build_wenku8_headers(
    profile: dict[str, Any],
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build headers dict from a config profile, merging any extra headers."""
    h = dict(profile.get("headers", {}))
    if extra_headers:
        h.update(extra_headers)
    # Remove Accept-Encoding — curl_cffi handles decompression automatically
    h.pop("Accept-Encoding", None)
    return h


def _fetch_wenku8_text(
    title: str,
    cookie: str | None = None,
) -> dict[str, Any]:
    """
    Search for a book on wenku8.net and fetch its page text.

    Uses saved browser headers from config/wenku8_headers.json for
    Cloudflare bypass (cf_clearance cookie + browser TLS fingerprint).
    Falls back to the passed cookie if no config file exists.

    Two-step process:
    1. Search for the title (GBK-encoded query) — mobile profile
    2. Fetch the first matching book's page — desktop profile
    """
    import html as html_mod

    result: dict[str, Any] = {"source": "wenku8", "found": False}

    # Load browser config (stored headers from Chrome DevTools)
    config = _load_wenku8_config()
    mobile_profile = config.get("profiles", {}).get("mobile") if config else None
    desktop_profile = config.get("profiles", {}).get("desktop") if config else None

    # Determine the cookie to use: explicit > config mobile > config desktop
    effective_cookie = cookie
    if not effective_cookie:
        if mobile_profile and mobile_profile.get("cookie"):
            effective_cookie = mobile_profile["cookie"]
        elif desktop_profile and desktop_profile.get("cookie"):
            effective_cookie = desktop_profile["cookie"]

    # Determine impersonation and headers per profile
    mobile_impersonate = (
        mobile_profile.get("impersonate", "chrome131_android")
        if mobile_profile else "chrome131_android"
    )
    desktop_impersonate = (
        desktop_profile.get("impersonate", "chrome146")
        if desktop_profile else "chrome146"
    )

    # Step 1: Search (mobile fingerprint)
    try:
        encoded_key = urllib.parse.quote(title.encode("gbk"))
    except UnicodeEncodeError:
        encoded_key = urllib.parse.quote(title.encode("utf-8"))

    search_headers = _build_wenku8_headers(
        mobile_profile or {},
        {"Referer": "https://www.wenku8.net/"},
    ) if mobile_profile else {
        "Referer": "https://www.wenku8.net/",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 "
            "Mobile Safari/537.36"
        ),
    }

    search_url = f"{WENKU8_SEARCH_URL}?searchtype=articlename&searchkey={encoded_key}"
    search_html = _curl_get(
        search_url,
        impersonate=mobile_impersonate,
        cookie=effective_cookie,
        headers=search_headers,
        encoding="gbk",
    )
    if not search_html:
        return result
    # Check for Cloudflare challenge
    if "Just a moment" in search_html:
        logger.warning("wenku8 search blocked by Cloudflare challenge")
        return result

    # Parse search results
    # wenku8 has "我要阅读" action links and actual book title links
    # Prefer links whose text is NOT "我要阅读" or empty/whitespace
    # href 可能不是第一个属性（如 style 在前），用 [^>]* 允许前面有任意属性
    all_book_links = re.findall(
        r'<a\s+[^>]*href="/book/(\d+)\.htm"[^>]*>([^<]+)</a>', search_html
    )
    # Filter out action buttons ("我要阅读") — keep actual book title links
    book_links = [
        m for m in all_book_links
        if m[1].strip() not in ("我要阅读", "我要閱讀", "")
    ]
    # Fallback: if no title links found, use action links as IDs
    if not book_links and all_book_links:
        book_links = all_book_links

    if not book_links:
        return result
        # Debug: save raw HTML for inspection
        logger.debug(f"wenku8 search raw (first 2000 chars): {search_html[:2000]}")
        return result

    result["search_results"] = [
        {"id": m[0], "title": html_mod.unescape(m[1]).strip()}
        for m in book_links[:10]
    ]
    result["url"] = WENKU8_BOOK_URL.format(book_links[0][0])
    result["found"] = True

    # Step 2: Fetch the first book's page (desktop fingerprint)
    book_url = WENKU8_BOOK_URL.format(book_links[0][0])

    book_headers = _build_wenku8_headers(
        desktop_profile or {},
        {"Referer": "https://www.wenku8.net/"},
    ) if desktop_profile else {
        "Referer": "https://www.wenku8.net/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    book_html = _curl_get(
        book_url,
        impersonate=desktop_impersonate,
        cookie=effective_cookie,
        headers=book_headers,
        encoding="gbk",
    )
    if book_html and "Just a moment" not in book_html:
        # Extract the main content area between <div id="content"> and sidebar
        # This captures metadata tables, description, and book info
        main_match = re.search(
            r'<div id="content">(.*?)(?:<div id="left">|<div class="main m_foot")',
            book_html,
            re.DOTALL,
        )
        text_source = main_match.group(1) if main_match else book_html
        result["text"] = _html_to_text(text_source)

    return result


# ── Main enrichment function ──────────────────────────────────────────────


async def _run_enrichment_impl(
    title: str,
    author: str | None = None,
    use_wikipedia: bool = True,
    use_moegirl: bool = True,
    use_wenku8: bool = True,
    wenku8_cookie: str | None = None,
    moegirl_cookie: str | None = None,
) -> dict[str, Any]:
    """
    Internal implementation: fetch raw text from multiple web sources.

    Returns the raw text content from each source.
    The LLM is responsible for understanding and extracting structured metadata
    from the returned text.
    """
    combined: dict[str, Any] = {
        "title": title,
        "author": author,
        "sources": {},
    }

    # Source 1: Wikipedia (no Cloudflare, uses urllib)
    if use_wikipedia:
        wiki_data = await _async_wikipedia(title)
        if wiki_data.get("found"):
            combined["sources"]["wikipedia"] = {
                "url": wiki_data.get("url", ""),
                "text": wiki_data.get("text", ""),
                "lang": wiki_data.get("lang", ""),
            }

    # Source 2: 萌娘百科 (Cloudflare → curl_cffi chrome146)
    if use_moegirl:
        moe_data = await _async_moegirl(title, moegirl_cookie)
        if moe_data.get("found"):
            moe_entry: dict[str, Any] = {
                "url": moe_data.get("url", ""),
                "text": moe_data.get("text", ""),
            }
            if moe_data.get("page_title"):
                moe_entry["page_title"] = moe_data["page_title"]
            combined["sources"]["moegirl"] = moe_entry

    # Source 3: wenku8 (Cloudflare → curl_cffi chrome131_android)
    if use_wenku8:
        wk_data = await _async_wenku8(title, wenku8_cookie)
        if wk_data.get("found"):
            wk_entry: dict[str, Any] = {
                "url": wk_data.get("url", ""),
                "text": wk_data.get("text", ""),
            }
            if wk_data.get("search_results"):
                wk_entry["search_results"] = wk_data["search_results"]
            combined["sources"]["wenku8"] = wk_entry

    return combined


async def _async_wikipedia(title: str) -> dict[str, Any]:
    import asyncio
    return await asyncio.to_thread(_fetch_wikipedia_extract, title)


async def _async_moegirl(title: str, cookie: str | None = None) -> dict[str, Any]:
    import asyncio
    return await asyncio.to_thread(_fetch_moegirl_text, title, cookie)


async def _async_wenku8(title: str, cookie: str | None = None) -> dict[str, Any]:
    import asyncio
    return await asyncio.to_thread(_fetch_wenku8_text, title, cookie)


# ── MCP tool registration ─────────────────────────────────────────────────


@mcp.tool()
async def enrich_book_metadata(
    title: str,
    author: str | None = None,
    use_wikipedia: bool = True,
    use_moegirl: bool = True,
    use_wenku8: bool = True,
    wenku8_cookie: str | None = None,
    moegirl_cookie: str | None = None,
) -> dict[str, Any]:
    """
    从网络获取书籍元数据（维基百科、萌娘百科、轻小说文库）。

    从多个公开来源获取页面的纯文本内容，供 LLM 进行自然语言理解和结构化提取。
    相比正则解析 HTML，这种方式更稳健——不依赖特定网页结构。

    各来源的访问方式：
    - 维基百科：公共 API，无需特殊配置
    - 萌娘百科：受 Cloudflare 保护，需要 curl_cffi + 桌面端 Chrome 指纹（自动处理）
    - wenku8.net：受 Cloudflare 保护，需要 curl_cffi + 移动端 Android 指纹（自动处理）
      优先读取 config/wenku8_headers.json 中保存的浏览器标头（含 cf_clearance cookie），
      如果未提供 wenku8_cookie 参数则自动使用配置文件中的 cookie。

    参数:
        title: 书名（中文或日文均可）
        author: 可选的作者名，用于缩小搜索范围
        use_wikipedia: 是否查询维基百科（默认 True）
        use_moegirl: 是否查询萌娘百科（默认 True）
        use_wenku8: 是否查询轻小说文库 wenku8.net（默认 True）
        wenku8_cookie: 可选，自定义 Cookie 头（留空则使用 config/wenku8_headers.json 中的保存值）
        moegirl_cookie: 可选，浏览器的完整 Cookie 头（在严格 Cloudflare 保护下使用）

    返回:
        包含各来源原始文本的字典：
        {
            "title": 查询的书名,
            "author": 提供的作者（可选）,
            "sources": {
                "wikipedia": { "url": ..., "text": ..., "lang": "ja/zh" },
                "moegirl": { "url": ..., "text": ..., "page_title": ... },
                "wenku8": { "url": ..., "text": ..., "search_results": [...] }
            }
        }

    示例:
        enrich_book_metadata(title="这段青春存在隐情", author="岸本和葉")
        enrich_book_metadata(title="魔法科高中的劣等生")
    """
    return await _run_enrichment_impl(
        title=title,
        author=author,
        use_wikipedia=use_wikipedia,
        use_moegirl=use_moegirl,
        use_wenku8=use_wenku8,
        wenku8_cookie=wenku8_cookie,
        moegirl_cookie=moegirl_cookie,
    )
