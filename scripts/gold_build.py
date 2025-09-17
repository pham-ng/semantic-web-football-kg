#!/usr/bin/env python3
import os
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

SILVER_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../silver/normalized/silver.ttl")
)
GOLD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../gold/ttl"))
SHAPES_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../shapes/core_shapes.ttl")
)
ONTOLOGY_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../ontology/core.ttl")
)

KG = Namespace("https://kg-football.vn/ontology#")
PROV = Namespace("http://www.w3.org/ns/prov#")
CC = Namespace("http://creativecommons.org/ns#")


def enrich_and_validate():
    g = Graph()
    if os.path.exists(ONTOLOGY_FILE):
        g.parse(ONTOLOGY_FILE, format="turtle")
    if os.path.exists(SILVER_FILE):
        g.parse(SILVER_FILE, format="turtle")

    # add minimal provenance and license to all subjects created in silver
    for s in set(g.subjects(RDF.type, None)):
        g.add((s, PROV.wasDerivedFrom, URIRef("https://vi.wikipedia.org")))
        g.add(
            (s, CC.license, URIRef("https://creativecommons.org/licenses/by-sa/4.0/"))
        )

    # TODO: Thêm SHACL validation thật bằng pyshacl nếu cần
    return g


def main():
    os.makedirs(GOLD_DIR, exist_ok=True)
    g = enrich_and_validate()
    out = os.path.join(GOLD_DIR, "gold.ttl")
    g.serialize(destination=out, format="turtle")
    print("Wrote", out)


if __name__ == "__main__":
    main()
