# KG Football VN (Semantic Web)

Pipeline: Bronze (crawl) → Silver (NER/RE + canonicalize + dedupe) → Linking (Silk) → Gold (OWL + SHACL + enrichment) → Fuseki → Public SPARQL + Dereferenceable URIs + HTML view.

## URI Design
- Base: `https://kg-football.vn/`
- Ontology: `https://kg-football.vn/ontology#`
- Resource: `https://kg-football.vn/resource/{type}/{label}`
- Human page: `https://kg-football.vn/page/resource/{type}/{label}`
- Principles: stable, readable, lower-case or PascalCase fragment, dereferenceable via content negotiation.

## Quick start
```bash
# 1) Bronze crawl (Wikipedia VI, wikitext)
# Lưu tại bronze/wiki_raw/*  | Tham số: --max-depth, --max-pages, --delay, --batch-size
python3 scripts/bronze_crawl_wiki.py --max-depth 3 --max-pages 25000 --delay 0.1 --batch-size 20

# (Tuỳ chọn) Bronze crawl (Web, lọc URL theo từ khoá bóng đá)
# Lưu tại bronze/raw_web/*  | Tham số: --seeds, --max-pages, --max-depth, --delay
python3 scripts/bronze_crawl_web.py --max-pages 25000 --max-depth 3 --delay 0.01

# 2) Silver transform (generate Turtle)
python3 scripts/silver_transform.py

# 3) Gold build (enrich + provenance + license)
python3 scripts/gold_build.py

# 4) Run local API (dereferenceable URIs)
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Try content negotiation
curl -H "Accept: text/turtle" http://localhost:8080/resource/player/Cong_Ph%C6%B0%E1%BB%A3ng
```

## Fuseki
```bash
cd fuseki
docker compose up -d
# open http://localhost:3030
```
