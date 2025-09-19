from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef

# Load file TTL
g = Graph()
g.parse("ontology/org.ttl", format="ttl")  

# Định nghĩa namespace
KG = Namespace("https://kg-football.vn/ontology#")
DBO = Namespace("http://dbpedia.org/ontology/")

# Mapping classes: kg:Class -> dbo:Class
class_mapping = {
    KG.Team: DBO.SportsTeam,
    KG.Club: DBO.FootballClub,
    KG.NationalTeam: DBO.NationalFootballTeam,
    KG.Coach: DBO.SoccerCoach,
    KG.Owner: DBO.Person,
    KG.Referee: DBO.Referee,
    KG.Stadium: DBO.Stadium
}

# Mapping properties: kg:property -> dbo:property
property_mapping = {
    KG.homeStadium: DBO.ground,
    KG.isHomeOf: DBO.ground,
    KG.manages: DBO.manager,
    KG.hasCoach: DBO.manager,
    KG.owns: DBO.owner,
    KG.hasOwner: DBO.owner,
    KG.venue: DBO.ground,
    KG.capacity: DBO.capacity,
    KG.foundedDate: DBO.foundingDate
}

# Add equivalentClass triples
for kg_class, dbo_class in class_mapping.items():
    g.add((kg_class, OWL.equivalentClass, dbo_class))

# Add equivalentProperty triples
for kg_prop, dbo_prop in property_mapping.items():
    g.add((kg_prop, OWL.equivalentProperty, dbo_prop))

# Xuất ra file TTL mới
g.serialize(destination="ontology/mapping/mapped_org.ttl", format="turtle")
print("Done")

