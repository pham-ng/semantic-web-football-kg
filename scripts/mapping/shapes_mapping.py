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