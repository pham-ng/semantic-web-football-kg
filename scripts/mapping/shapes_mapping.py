#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Create a stub mapping file for SHACL shapes (no DBpedia mapping).
- Reads ontology/shapes.ttl
- Produces ontology/mapping/map_shapes_stub.ttl
- Adds an ontology header + owl:imports the main ontology
- For each sh:NodeShape with sh:targetClass, emits rdfs:seeAlso links (for documentation)

Why: keep folder structure consistent with other mapping files while making it explicit
that SHACL shapes are constraints, not vocabulary to be mapped to DBpedia.
"""

from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal
from rdflib.namespace import DCTERMS

# ---- INPUT / OUTPUT ----
SHAPES_TTL  = "ontology/shapes.ttl"
OUTPUT_TTL  = "ontology/mapping/map_shapes_stub.ttl"

# ---- NAMESPACES ----
KG   = Namespace("https://kg-football.vn/ontology#")
ONTO = URIRef("https://kg-football.vn/ontology")
MAP  = URIRef("https://kg-football.vn/ontology/mapping/shapes")

SH   = Namespace("http://www.w3.org/ns/shacl#")
SCM  = Namespace("http://schema.org/")
TIME = Namespace("http://www.w3.org/2006/time#")

def main():
    # load shapes
    g_in = Graph()
    g_in.parse(SHAPES_TTL, format="turtle")

    # prepare output graph
    g = Graph()
    g.bind("kg", KG)
    g.bind("sh", SH)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("dct", DCTERMS)
    g.bind("schema", SCM)
    g.bind("time", TIME)

    # ontology header (stub)
    g.add((MAP, RDF.type, OWL.Ontology))
    g.add((MAP, DCTERMS.title, Literal("KG-Football SHACL (no DBpedia mapping)", lang="en")))
    g.add((MAP, RDFS.comment, Literal(
        "SHACL shapes define constraints for data validation; they are not mapped to DBpedia ontology.",
        lang="en"
    )))
    # import the main ontology so tools can resolve kg:* terms
    g.add((MAP, OWL.imports, ONTO))

    # OPTIONAL: document NodeShapes -> their target classes via rdfs:seeAlso
    for node_shape in g_in.subjects(RDF.type, SH.NodeShape):
        for cls in g_in.objects(node_shape, SH.targetClass):
            g.add((node_shape, RDFS.seeAlso, cls))

    # write
    g.serialize(OUTPUT_TTL, format="turtle")
    print(f"Done: wrote {OUTPUT_TTL}")

if __name__ == "__main__":
    main()
