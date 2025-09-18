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
from typing import Set, List, Dict, Tuple

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../bronze/wiki_raw"))
DONE_FILE = os.path.join(OUTPUT_DIR, "..", "wiki_done.txt")
ERROR_FILE = os.path.join(OUTPUT_DIR, "..", "wiki_error.txt")

WIKI_API = "https://vi.wikipedia.org/w/api.php"

# Mặc định (có thể override qua CLI)
DEFAULT_MAX_DEPTH = 3
DEFAULT_MAX_PAGES = 5000
DEFAULT_DELAY = 0.3
BATCH_SIZE = 20  # số title mỗi lần gọi API

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
    "giải vô địch",
    "đội tuyển",
    "huấn luyện viên",
    "sân vận động",
    "aff",
    "sea games",
    "world cup",
    "cầu thủ",
    "ngoại hạng",
    "champions league",
    "champions cup",
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
    "Lịch sử bóng đá Việt Nam",
    "Liên đoàn bóng đá Việt Nam",
    "Sân vận động Mỹ Đình",
    "Huấn luyện viên Park Hang-seo",
    "Giải hạng Nhất Quốc gia Việt Nam",
    "World Cup",
    "Champion League",
    "Ngoại hạng Anh",
]


def get_session() -> requests.Session:
    session = requests.Session()
    headers = {
        "User-Agent": "KG-Football-Bot/0.1 (+https://kg-football.vn; contact=admin@kg-football.vn)",
        "Accept": "application/json",
    }
    session.headers.update(headers)
    retry = Retry(
        total=3,
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


def fetch_pages_wikitext(titles: List[str]) -> Dict[str, dict]:
    """Lấy wikitext đầy đủ cho danh sách titles (batch). Trả về map title -> page dict."""
    params = {
        "action": "query",
        "prop": "revisions|info",
        "titles": "|".join(titles),
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
    result: Dict[str, dict] = {}
    # resolve redirects map
    redirects = {}
    for rd in j.get("query", {}).get("redirects", []) or []:
        redirects[rd.get("from")] = rd.get("to")
    for p in j.get("query", {}).get("pages", []) or []:
        title = p.get("title")
        if not title:
            continue
        result[title] = p
    # also map original request titles via redirects
    for t in titles:
        if t in redirects and redirects[t] in result:
            result[t] = result[redirects[t]]
    return result


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


def run(max_depth: int, max_pages: int, delay: float):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    done = set()
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE, "r", encoding="utf-8") as f:
            done = set(line.strip() for line in f if line.strip())

    permanent_error_skip = load_permanent_errors()

    saved_count = 0
    queue: deque[Tuple[str, int]] = deque([(t, 0) for t in TOPICS])
    visited = set(done) | set(permanent_error_skip)

    with tqdm(total=max_pages, desc="Crawling Wikipedia (wikitext)") as pbar:
        while queue and saved_count < max_pages:
            # build a batch
            batch_titles: List[str] = []
            depth_by_title: Dict[str, int] = {}
            while queue and len(batch_titles) < min(BATCH_SIZE, max_pages - saved_count):
                title, depth = queue.popleft()
                if title in visited:
                    continue
                visited.add(title)
                batch_titles.append(title)
                depth_by_title[title] = depth

            if not batch_titles:
                break

            try:
                pages_map = fetch_pages_wikitext(batch_titles)
                for original_title in batch_titles:
                    page = pages_map.get(original_title)
                    if not page:
                        append_error(original_title, 404, False, "page_not_found")
                        continue
                    save_page_json(original_title, {"mode": "wikitext", "query": {"pages": [page]}})
                    with open(DONE_FILE, "a", encoding="utf-8") as f:
                        f.write(original_title + "\n")
                    saved_count += 1
                    pbar.update(1)

                    # expand links if allowed
                    depth = depth_by_title.get(original_title, 0)
                    if depth < max_depth:
                        try:
                            for lt in fetch_links(original_title, delay):
                                if lt not in visited and is_footballish(lt):
                                    queue.append((lt, depth + 1))
                        except Exception as le:
                            print(f"⚠️ Link expand error for {original_title}: {le}")

            except requests.HTTPError as he:
                status = getattr(he.response, "status_code", None) or 0
                for bt in batch_titles:
                    append_error(bt, status, status in RETRYABLE_STATUS, str(he))
            except Exception as e:
                for bt in batch_titles:
                    append_error(bt, 0, True, str(e))
            finally:
                time.sleep(delay)

    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            {"source": "wikipedia vi", "items": list(visited)},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"📦 Manifest saved to {manifest_path}")


def parse_args():
    p = argparse.ArgumentParser(description="Wikipedia VI football crawler (wikitext, batched)")
    p.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    p.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    return p.parse_args()


def main():
    args = parse_args()
    global BATCH_SIZE
    BATCH_SIZE = args.batch_size
    run(
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
