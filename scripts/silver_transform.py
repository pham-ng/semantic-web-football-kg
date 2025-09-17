#!/usr/bin/env python3
import os
import json
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, FOAF

BRONZE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../bronze/raw"))
SILVER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../silver/normalized")
)
KG = Namespace("https://kg-football.vn/ontology#")
RES = Namespace("https://kg-football.vn/resource/")


def canonicalize_name(name: str) -> str:
    return name.strip().replace(" ", "_")


def build_graph_from_bronze():
    g = Graph()
    g.bind("kg", KG)
    g.bind("res", RES)
    g.bind("foaf", FOAF)

    # Minimal demo: nếu tiêu đề có "FC" xem là Club, ngược lại là Player
    for fn in os.listdir(BRONZE_DIR):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(BRONZE_DIR, fn), encoding="utf-8") as f:
            data = json.load(f)
        pages = data.get("query", {}).get("pages", {})
        for _, page in pages.items():
            title = page.get("title")
            if not title:
                continue
            if "FC" in title or "Câu lạc bộ" in title:
                club_id = canonicalize_name(title)
                club = RES[f"club/{club_id}"]
                g.add((club, RDF.type, KG.Club))
                g.add((club, RDFS.label, Literal(title, lang="vi")))
            else:
                pid = canonicalize_name(title)
                player = RES[f"player/{pid}"]
                g.add((player, RDF.type, KG.Player))
                g.add((player, FOAF.name, Literal(title, lang="vi")))
    return g


def main():
    os.makedirs(SILVER_DIR, exist_ok=True)
    g = build_graph_from_bronze()
    out = os.path.join(SILVER_DIR, "silver.ttl")
    g.serialize(destination=out, format="turtle")
    print("Wrote", out)


if __name__ == "__main__":
    main()
