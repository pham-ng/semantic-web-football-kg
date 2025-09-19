from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef

# Load file TTL
g = Graph()
g.parse("ontology/geo.ttl", format="ttl") 

# Namespace
KG = Namespace("https://kg-football.vn/ontology#")
DBO = Namespace("http://dbpedia.org/ontology/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")

# Mapping classes
class_mapping = {
    KG.Place: DBO.Place,
    KG.City: DBO.City,
    KG.Country: DBO.Country
}

# Mapping properties
property_mapping = {
    KG.locatedIn: DBO.isPartOf,  
    KG.geometry: GEO.hasGeometry,
    KG.wkt: GEO.asWKT
}

# Thêm owl:equivalentClass cho classes
for kg_class, dbo_class in class_mapping.items():
    g.add((kg_class, OWL.equivalentClass, dbo_class))

# Thêm owl:equivalentProperty cho properties
for kg_prop, dbo_prop in property_mapping.items():
    g.add((kg_prop, OWL.equivalentProperty, dbo_prop))

# Xuất file TTL mới
g.serialize(destination="ontology/mapping/mapped_geo.ttl", format="turtle")
print("Done")

