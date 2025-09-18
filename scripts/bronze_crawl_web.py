#!/usr/bin/env python3
import os
import re
import time
import argparse
import json
from urllib.parse import urljoin, urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from tqdm import tqdm
from collections import deque
from urllib import robotparser

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../bronze/raw_web"))
DONE_FILE = os.path.join(RAW_DIR, "..", "web_done.txt")
ERROR_FILE = os.path.join(RAW_DIR, "..", "web_error.txt")

DEFAULT_MAX_PAGES = 5000
DEFAULT_DELAY = 0.1
DEFAULT_DEPTH = 2
DEFAULT_TIMEOUT = 10

# Có thể thay seeds qua CLI
SEED_HOSTS = {
    "https://vff.org.vn",
    "https://thethao.vnexpress.net",
    "https://baomoi.com/bong-da-viet-nam.epi",
    "https://thanhnien.vn/the-thao/bong-da-viet-nam.htm",
    "https://www.24h.com.vn/bong-da-viet-nam-c182.html",
    "https://vietnamnet.vn/the-thao/bong-da-viet-nam",
    "https://vnexpress.net/bong-da/viet-nam",
    "https://bongdaplus.vn",
    "https://nhandan.vn/tu-khoa/bongdaVietNam-tag49139.html",
    "https://dantri.com.vn/chu-de/doi-tuyen-bong-da-quoc-gia-viet-nam-4218.htm",
    "https://bongda.com.vn/",
}

USER_AGENT = (
    "KG-Football-WebBot/0.1 (+https://kg-football.vn; contact=admin@kg-football.vn)"
)
RETRYABLE_STATUS = {403, 408, 429, 500, 502, 503, 504}

FOOTBALL_URL_KEYWORDS = [
    "bongda",
    "bong-da",
    "bong_da",
    "bongdanu",
    "bong-da-nu",
    "vleague",
    "v-league",
    "v.league",
    "vff",
    "vdv",
    "clb",
    "fc",
    "futsal",
    "worldcup",
    "world-cup",
    "world_cup",
    "sea-games",
    "seagames",
    "aff",
    "aff-cup",
    "cup",
    "champions-league",
    "championsleague",
    "ngoai-hang",
    "premier-league",
    "san-van-dong",
    "sanvandong",
    "doi-tuyen",
    "doi-bong",
    "cau-thu",
    "cauthu",
    "huan-luyen-vien",
    "huanluyenvien",
]


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "vi, en;q=0.8",
        }
    )
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=list(RETRYABLE_STATUS),
        allowed_methods=["GET"],
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def normalize_url(base: str, link: str) -> str:
    try:
        u = urljoin(base, link)
        pu = urlparse(u)
        if not pu.scheme.startswith("http"):
            return ""
        return u.split("#")[0]
    except Exception:
        return ""


def allowed_by_robots(url: str, rp_cache: dict):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    if robots_url not in rp_cache:
        rp = robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            resp = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=5)
            if resp.status_code >= 400:
                rp_cache[robots_url] = None
                return True, f"robots_http_{resp.status_code}:{robots_url}"
            content = resp.text
            rp.parse(content.splitlines())
            rp_cache[robots_url] = rp
        except Exception:
            rp_cache[robots_url] = None
            return True, f"robots_read_failed:{robots_url}"
    rpp = rp_cache.get(robots_url)
    if rpp is None:
        return True, f"robots_unavailable:{robots_url}"
    can = rpp.can_fetch(USER_AGENT, url)
    return (True, "") if can else (False, "robots_disallow")


def save_page(url: str, html: str, text: str):
    os.makedirs(RAW_DIR, exist_ok=True)
    safe_path = re.sub(r"[^a-zA-Z0-9._-]", "_", url)
    base = os.path.join(RAW_DIR, f"page_{safe_path}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(
            {"url": url, "html_file": base + ".html", "text_file": base + ".txt"},
            f,
            ensure_ascii=False,
            indent=2,
        )
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(html)
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(text)


def is_footballish_url(url: str, seed_hosts: set = SEED_HOSTS) -> bool:
    # pu = urlparse(url)
    # host = pu.netloc
    # if host in seed_hosts:
    #     return True
    lu = url.lower()
    return any(k in lu for k in FOOTBALL_URL_KEYWORDS)


def extract_links(url: str, html: str, seed_hosts: set = SEED_HOSTS) -> list:
    out = []
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        u = normalize_url(url, a["href"])
        if not u:
            continue
        if not is_footballish_url(u, seed_hosts):
            continue
        out.append(u)
    return out


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def run(seeds: list, max_pages: int, max_depth: int, delay: float, timeout: int):
    session = get_session()
    rp_cache = {}

    done = set()
    if os.path.exists(DONE_FILE):
        with open(DONE_FILE, "r", encoding="utf-8") as f:
            done = set(line.strip() for line in f if line.strip())

    results = 0
    queue = deque([(s, 0) for s in seeds])
    visited = set(done)
    seed_hosts = {urlparse(s).netloc for s in seeds}

    with tqdm(total=max_pages, desc="Crawling Web BFS") as pbar:
        while queue and results < max_pages:
            url, depth = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            try:
                allowed, reason = allowed_by_robots(url, rp_cache)
                if not allowed:
                    with open(ERROR_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{url}\t{reason}\n")
                    continue
                r = session.get(url, timeout=timeout)
                r.raise_for_status()
                html = r.text
                text = clean_text(html)
                save_page(url, html, text)
                with open(DONE_FILE, "a", encoding="utf-8") as f:
                    f.write(url + "\n")
                results += 1
                pbar.update(1)

                if depth < max_depth:
                    for u in extract_links(url, html, seed_hosts):
                        if u not in visited:
                            queue.append((u, depth + 1))

            except Exception as e:
                with open(ERROR_FILE, "a", encoding="utf-8") as f:
                    f.write(f"{url}\t{e}\n")
            finally:
                time.sleep(delay)


def parse_args():
    p = argparse.ArgumentParser(description="Generic web crawler (BFS) for Bronze")
    p.add_argument("--seeds", nargs="+", default=list(SEED_HOSTS), help="Seed URLs")
    p.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    p.add_argument("--max-depth", type=int, default=DEFAULT_DEPTH)
    p.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    return p.parse_args()


def main():
    args = parse_args()
    run(args.seeds, args.max_pages, args.max_depth, args.delay, args.timeout)


if __name__ == "__main__":
    main()
