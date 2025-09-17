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
# 1) Bronze crawl (Wikipedia VI)
python3 scripts/bronze_crawl_wiki.py

# 2) Silver transform (generate Turtle)
python3 scripts/silver_transform.py

# 3) Gold build (enrich + provenance + license)
python3 scripts/gold_build.py

# 4) Run local API (dereferenceable URIs)
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Try
curl -H "Accept: text/turtle" http://localhost:8080/resource/player/Cong_Ph%C6%B0%E1%BB%A3ng
```

## Fuseki
```bash
cd fuseki
docker compose up -d
# open http://localhost:3030
```
