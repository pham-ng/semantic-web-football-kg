#!/usr/bin/env python3
import os
import json
import re
import time
import argparse
from urllib.parse import quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
from collections import deque
from typing import Set

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../bronze/raw"))
DONE_FILE = os.path.join(OUTPUT_DIR, "..", "done.txt")
ERROR_FILE = os.path.join(OUTPUT_DIR, "..", "error.txt")

WIKI_API = "https://vi.wikipedia.org/w/api.php"
REST_SUMMARY = "https://vi.wikipedia.org/api/rest_v1/page/summary/"

# Mặc định (có thể override qua CLI)
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_PAGES = 25000
DEFAULT_DELAY = 0.3
DEFAULT_FULL = True  # False: chỉ intro, True: toàn bộ phần văn bản
DEFAULT_MODE = "extract"  # extract | wikitext | html

# Phân loại lỗi
RETRYABLE_STATUS = {403, 408, 429, 500, 502, 503, 504, 520, 522}
PERMANENT_STATUS = {400, 401, 404, 410}

# Từ khóa để lọc theo chủ đề bóng đá (đơn giản)
FOOTBALL_KEYWORDS = [
    "bóng đá",
    "bong da",
    "fc",
    "v.league",
    "vleague",
    "cup",
    "futsal",
    "giải vô địch",
    "đội tuyển",
    "huấn luyện viên",
    "sân vận động",
    "aff",
    "sea games",
    "cầu thủ",
]

TOPICS = [
    "Đội tuyển bóng đá quốc gia Việt Nam",
    "Cầu thủ bóng đá Việt Nam",
    "Câu lạc bộ bóng đá Việt Nam",
    "Đội tuyển bóng đá nữ quốc gia Việt Nam",
    "Đội tuyển bóng đá U23 Việt Nam",
    "V.League 1",
    "Cúp Quốc gia Việt Nam",
    "AFF Cup",
    "SEA Games bóng đá",
    "Giải vô địch bóng đá Đông Nam Á",
    "Hà Nội FC",
    "Hoàng Anh Gia Lai",
    "Công Phượng",
    "Nguyễn Quang Hải",
    "Lê Công Vinh",
    "Nguyễn Công Phượng",
    "Lương Xuân Trường",
    "Bóng đá trẻ Việt Nam",
    "Bóng đá nữ Việt Nam",
    "Futsal Việt Nam",
    "Lịch sử bóng đá Việt Nam",
    "Liên đoàn bóng đá Việt Nam",
    "Sân vận động Mỹ Đình",
    "Huấn luyện viên Park Hang-seo",
    "Giải hạng Nhất Quốc gia Việt Nam",
]


def get_session() -> requests.Session:
    session = requests.Session()
    headers = {
        "User-Agent": "KG-Football-Bot/0.1 (+https://kg-football.vn; contact=admin@kg-football.vn)",
        "Accept": "application/json",
    }
    session.headers.update(headers)
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=list(RETRYABLE_STATUS),
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


SESSION = get_session()


def fetch_page(title: str, *, mode: str = DEFAULT_MODE, full: bool = DEFAULT_FULL):
    """Trả về dữ liệu trang theo mode:
    - extract: dùng extracts (intro hoặc full text)
    - wikitext: dùng revisions API để lấy wikitext đầy đủ
    - html: dùng action=parse&prop=text để lấy HTML render
    """
    if mode == "wikitext":
        params = {
            "action": "query",
            "prop": "revisions|info",
            "titles": title,
            "rvprop": "content",
            "rvslots": "main",
            "format": "json",
            "formatversion": 2,
            "utf8": 1,
            "maxlag": 5,
            "redirects": 1,
            "inprop": "url",
        }
        r = SESSION.get(WIKI_API, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
        return {"mode": mode, "query": j.get("query", {})}, r.status_code

    if mode == "html":
        params = {
            "action": "parse",
            "page": title,
            "prop": "text|links|templates",
            "format": "json",
            "utf8": 1,
            "maxlag": 5,
            "redirects": 1,
        }
        r = SESSION.get(WIKI_API, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
        return {"mode": mode, "parse": j.get("parse", {})}, r.status_code

    # default: extract
    params = {
        "action": "query",
        "prop": "extracts|pageimages|info",
        "explaintext": True,
        "inprop": "url",
        "format": "json",
        "formatversion": 2,
        "utf8": 1,
        "maxlag": 5,
        "titles": title,
        "pithumbsize": 300,
        "redirects": 1,
    }
    if not full:
        params["exintro"] = True

    r = SESSION.get(WIKI_API, params=params, timeout=30)
    if r.status_code in (403, 429):
        # Fallback sang REST summary API (chỉ tóm tắt)
        ru = REST_SUMMARY + quote(title)
        r2 = SESSION.get(ru, timeout=30)
        r2.raise_for_status()
        j = r2.json()
        page = {
            "title": j.get("title", title),
            "extract": j.get("extract", ""),
            "content_urls": j.get("content_urls", {}),
            "thumbnail": j.get("thumbnail", {}),
        }
        return {"mode": mode, "query": {"pages": [page]}}, r.status_code
    r.raise_for_status()
    j = r.json()
    return {"mode": mode, "query": j.get("query", {})}, r.status_code


def fetch_links(title: str, delay: float):
    links = []
    params = {
        "action": "query",
        "prop": "links",
        "titles": title,
        "plnamespace": 0,
        "pllimit": 100,
        "format": "json",
        "formatversion": 2,
        "utf8": 1,
        "maxlag": 5,
    }
    cont = None
    while True:
        if cont:
            params.update({"plcontinue": cont})
        r = SESSION.get(WIKI_API, params=params, timeout=30)
        if r.status_code in (403, 429):
            time.sleep(max(1.0, delay))
            continue
        r.raise_for_status()
        j = r.json()
        pages = j.get("query", {}).get("pages", [])
        if pages:
            for p in pages:
                for l in p.get("links", []):
                    t = l.get("title")
                    if t:
                        links.append(t)
        cont = j.get("continue", {}).get("plcontinue")
        if not cont:
            break
    return links


def slugify(name: str) -> str:
    s = re.sub(r"\s+", "_", name.strip())
    s = s.replace("/", "_")
    return quote(s)


def is_footballish(title: str) -> bool:
    lower = title.lower()
    return any(k in lower for k in FOOTBALL_KEYWORDS)


def save_page_json(title: str, data: dict):
    fn = os.path.join(OUTPUT_DIR, f"wiki_{slugify(title)}.json")
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fn


def load_permanent_errors() -> Set[str]:
    skip = set()
    if os.path.exists(ERROR_FILE):
        with open(ERROR_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                # format: title\tstatus\tretryable\ttimestamp\tmessage
                if len(parts) >= 3:
                    title, _, retryable = parts[0], parts[1], parts[2]
                    if retryable == "0":
                        skip.add(title)
    return skip


def append_error(title: str, status: int, retryable: bool, message: str):
    ts = int(time.time())
    with open(ERROR_FILE, "a", encoding="utf-8") as f:
        f.write(f"{title}\t{status}\t{1 if retryable else 0}\t{ts}\t{message}\n")


def run(max_depth: int, max_pages: int, delay: float, full: bool, mode: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    done = set()
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE, "r", encoding="utf-8") as f:
            done = set(line.strip() for line in f if line.strip())

    permanent_error_skip = load_permanent_errors()

    results = []
    queue = deque([(t, 0) for t in TOPICS])
    visited = set(done) | set(permanent_error_skip)

    with tqdm(total=max_pages, desc="Crawling Wikipedia BFS") as pbar:
        while queue and (len(results) + len(done)) < max_pages:
            title, depth = queue.popleft()
            if title in visited:
                continue
            visited.add(title)
            try:
                data, status = fetch_page(title, mode=mode, full=full)
                results.append({"title": title, "data": data})
                fn = save_page_json(title, data)
                with open(DONE_FILE, "a", encoding="utf-8") as f:
                    f.write(title + "\n")
                pbar.update(1)

                if depth < max_depth:
                    try:
                        for lt in fetch_links(title, delay):
                            if lt not in visited and is_footballish(lt):
                                queue.append((lt, depth + 1))
                    except Exception as le:
                        print(f"⚠️ Link expand error for {title}: {le}")

            except requests.HTTPError as he:
                status = getattr(he.response, "status_code", None) or 0
                retryable = status in RETRYABLE_STATUS
                print(f"❌ Error fetching {title}: {status} retryable={retryable}")
                append_error(title, status, retryable, str(he))
            except Exception as e:
                print(f"❌ Error fetching {title}: {e}")
                append_error(title, 0, True, str(e))
            finally:
                time.sleep(delay)

    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            {"source": "wikipedia vi", "items": [r["title"] for r in results]},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"📦 Manifest saved to {manifest_path}")


def parse_args():
    p = argparse.ArgumentParser(description="Wikipedia VI football crawler (BFS)")
    p.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    p.add_argument(
        "--full", action="store_true", help="Tải toàn bộ extract thay vì chỉ intro"
    )
    p.add_argument(
        "--mode", choices=["extract", "wikitext", "html"], default=DEFAULT_MODE
    )
    return p.parse_args()


def main():
    args = parse_args()
    run(
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        delay=args.delay,
        full=args.full,
        mode=args.mode,
    )


if __name__ == "__main__":
    main()
