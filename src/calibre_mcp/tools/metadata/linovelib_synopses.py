"""
linovelib 分卷简介抓取工具。

从 linovelib.com 获取轻小说的分卷简介信息。
需要已登录的浏览器标头（含 cf_clearance cookie）保存在 config/linovelib_headers.json 中。
"""

import json
import re
import time
from pathlib import Path
from typing import Any

from ...logging_config import get_logger
from ...server import mcp

logger = get_logger("calibremcp.tools.metadata.linovelib")

LINOVELIB_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "config" / "linovelib_headers.json"
)

CURL_AVAILABLE = False
try:
    from curl_cffi import requests as curl_requests
    CURL_AVAILABLE = True
except ImportError:
    pass


def _load_config() -> dict[str, Any] | None:
    """Load saved browser headers from config file."""
    try:
        if LINOVELIB_CONFIG_PATH.exists():
            with open(LINOVELIB_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load linovelib config: {e}")
    return None


def _build_session(cookie: str | None = None) -> Any | None:
    """Build a curl_cffi session with saved browser headers."""
    if not CURL_AVAILABLE:
        logger.warning("curl_cffi not installed")
        return None

    from curl_cffi import requests

    config = _load_config()
    profile = config.get("profiles", {}).get("desktop") if config else None

    s = requests.Session()
    if profile:
        s.impersonate = profile.get("impersonate", "chrome146")
        s.headers["User-Agent"] = profile.get("user_agent", "")
        # Use explicit cookie > config cookie
        effective_cookie = cookie or profile.get("cookie", "")
        s.headers["Cookie"] = effective_cookie
        for k, v in profile.get("headers", {}).items():
            if k.lower() not in ("accept-encoding", "cookie", "user-agent"):
                s.headers[k] = v
    else:
        # Fallback defaults
        s.impersonate = "chrome146"
        if cookie:
            s.headers["Cookie"] = cookie

    # Essential headers always present
    s.headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    s.headers.setdefault("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
    s.headers.setdefault("Referer", "https://www.linovelib.com/")

    return s


def _search_book(s: Any, title: str) -> dict[str, Any] | None:
    """
    Search for a book on linovelib.

    Returns dict with 'id' and 'title', or None if not found.
    """
    resp = s.post(
        "https://www.linovelib.com/S6/",
        data={"searchkey": title},
        timeout=30,
    )
    if resp.status_code != 200:
        logger.debug(f"linovelib search returned HTTP {resp.status_code}")
        return None

    m = re.search(
        r'<a href="/novel/(\d+).html"[^>]*>(.*?)</a>',
        resp.text,
    )
    if m:
        # Strip any HTML tags (like <span class="hot">) to get the plain text title
        t = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        # Filter out navigation/breadcrumb links (too short or non-book titles)
        if len(t) > 1 and t not in ('下页', '上一页', '下一页', '尾页', '首页'):
            return {"id": m.group(1), "title": t}

    # Single-result redirect: linovelib redirects to book detail page
    # Detect by checking for .book-html-box or book-detail sections
    if 'book-html-box' in resp.text or 'book-detail' in resp.text:
        # Extract book ID from breadcrumb
        m2 = re.search(
            r'<a href="/novel/(\d+)\.html"[^>]*>([^<]+)</a>',
            resp.text,
        )
        if m2:
            t = m2.group(2).strip()
            if len(t) > 1:
                return {"id": m2.group(1), "title": t}
    return None


def _extract_volumes(s: Any, book_id: str) -> list[dict[str, str]]:
    """
    Extract all volume links from a novel detail page.

    Returns list of {vol_id, title} in descending order (latest first).
    """
    resp = s.get(
        f"https://www.linovelib.com/novel/{book_id}.html",
        timeout=30,
    )
    if resp.status_code != 200:
        return []

    vols = re.findall(
        rf'<a href="/novel/{book_id}/vol_(\d+)\.html"[^>]*title="([^"]+)"',
        resp.text,
    )
    return [{"vol_id": v[0], "title": v[1]} for v in vols]


def _strip_html(html_text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    text = re.sub(r"^\s+|\s+$", "", text, flags=re.MULTILINE)
    return text.strip()


def _fetch_volume_synopsis(s: Any, book_id: str, vol_id: str) -> str | None:
    """
    Fetch a single volume page and extract its synopsis.

    Primary source: <div class="book-dec volume-dec"> (full text, no truncation).
    Fallback: <meta name="description">.
    Final fallback: page body text extraction.
    """
    url = f"https://www.linovelib.com/novel/{book_id}/vol_{vol_id}.html"
    resp = s.get(url, timeout=30)
    if resp.status_code != 200:
        return None

    # Method 1: book-dec volume-dec div (full synopsis, no truncation)
    m = re.search(
        r'<div class="book-dec volume-dec">(.*?)</div>',
        resp.text,
        re.DOTALL,
    )
    if m:
        text = _strip_html(m.group(1))
        # Remove "别名" section and everything after
        text = re.split(r"别名[：:]", text)[0].strip()
        if text:
            return text

    # Method 2: meta description (may be truncated, may include title prefix)
    m = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
        resp.text,
    )
    if m:
        text = m.group(1)
        # Strip the leading title prefix: "才女的侍从 10(别名~ 10)内容简介："
        text = re.sub(r"^.*?[\)）]\s*内容简介[：:]", "", text).strip()
        text = re.sub(r"^.*?[\)）]\s*", "", text).strip()
        if text:
            return text

    # Method 3: body text extraction (last resort)
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", resp.text, flags=re.DOTALL)
    clean = re.sub(r"<[^>]+>", "\n", clean)
    lines = [l.strip() for l in clean.split("\n") if l.strip()]

    syn_lines = []
    started = False
    markers = {"序章", "第一章", "目录", "插图", "后记", "Special", "特典"}
    for line in lines:
        if not started:
            if "最后更新" in line or len(line) > 15:
                started = True
                if len(line) > 15:
                    syn_lines.append(line)
        else:
            if line in markers or re.match(r"第[一二三四五六七八九十]", line):
                break
            syn_lines.append(line)

    text = "\n".join(syn_lines)
    text = re.sub(r"^\d[\d\.\s，,\w]*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() or None


def _fetch_volumes_synopses(
    s: Any, book_id: str, volumes: list[dict[str, str]], max_volumes: int
) -> list[dict[str, Any]]:
    """Fetch synopses for up to max_volumes, with rate limiting."""
    results = []
    target_vols = volumes[:max_volumes] if max_volumes > 0 else volumes

    for i, vol in enumerate(target_vols):
        time.sleep(0.5)  # Rate limit between volume page requests
        synopsis = _fetch_volume_synopsis(s, book_id, vol["vol_id"])
        results.append({
            "title": vol["title"],
            "synopsis": synopsis or "",
        })
        if synopsis:
            logger.debug(f"Got synopsis for {vol['title']}")
        else:
            logger.warning(f"No synopsis for {vol['title']}")

    return results


@mcp.tool()
async def fetch_volume_synopses(
    title: str,
    max_volumes: int = 10,
    cookie: str | None = None,
) -> dict[str, Any]:
    """
    从 linovelib.com 获取轻小说的分卷简介。

    需要已登录的浏览器标头文件 config/linovelib_headers.json。
    如果 cookie 过期，可在浏览器重新登录后更新该文件中的 cookie 字段。

    搜索频率限制为 5 秒，自动处理。

    参数:
        title: 书名
        max_volumes: 最大获取卷数（默认 10，设为 -1 获取全部）
        cookie: 可选，自定义 Cookie 头（留空使用配置文件）

    返回:
        {
            "title": 书名,
            "book_id": linovelib 上的书籍 ID,
            "total_volumes": 总卷数,
            "fetched": 实际获取的卷数,
            "volumes": [
                {"title": "魔女之旅 25", "synopsis": "..."},
                {"title": "魔女之旅 24", "synopsis": "..."},
                ...
            ]
        }
    """
    import asyncio

    def _sync_impl() -> dict[str, Any]:
        s = _build_session(cookie)
        if not s:
            return {"error": "curl_cffi 不可用，无法访问 Cloudflare 保护的网站"}

        # Step 1: Search
        time.sleep(0.5)  # Small initial delay
        book = _search_book(s, title)
        if not book:
            return {
                "title": title,
                "error": f"在 linovelib 上未找到「{title}」",
            }

        # Step 2: Get volume list
        volumes = _extract_volumes(s, book["id"])
        if not volumes:
            return {
                "title": book["title"],
                "book_id": book["id"],
                "total_volumes": 0,
                "fetched": 0,
                "volumes": [],
                "error": "未找到卷列表",
            }

        # Step 3: Fetch synopses
        actual_max = max_volumes if max_volumes > 0 else len(volumes)
        synopses = _fetch_volumes_synopses(s, book["id"], volumes, actual_max)

        return {
            "title": book["title"],
            "book_id": book["id"],
            "total_volumes": len(volumes),
            "fetched": len(synopses),
            "volumes": synopses,
        }

    return await asyncio.to_thread(_sync_impl)
