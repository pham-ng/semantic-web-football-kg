from rdflib import Graph, Namespace, OWL

# --- Namespaces ---
KG = Namespace("https://kg-football.vn/ontology#")
DBO = Namespace("http://dbpedia.org/ontology/")

# --- Load ontology
g = Graph()
g.parse("ontology/people.ttl", format="turtle")  

# --- Bind namespaces ---
g.bind("kg", KG)
g.bind("dbo", DBO)

# --- Thêm mapping KG -> DBpedia ---
g.add((KG.Player, OWL.equivalentClass, DBO.SoccerPlayer))
g.add((KG.Goalkeeper, OWL.equivalentClass, DBO.Goalkeeper))
g.add((KG.Defender, OWL.equivalentClass, DBO.Defender))
g.add((KG.Midfielder, OWL.equivalentClass, DBO.Midfielder))
g.add((KG.Forward, OWL.equivalentClass, DBO.Forward))

g.add((KG.birthPlace, OWL.equivalentProperty, DBO.birthPlace))
g.add((KG.nationality, OWL.equivalentProperty, DBO.nationality))
g.add((KG.height, OWL.equivalentProperty, DBO.height))
g.add((KG.weight, OWL.equivalentProperty, DBO.weight))
g.add((KG.primaryPosition, OWL.equivalentProperty, DBO.position))
g.add((KG.secondaryPosition, OWL.equivalentProperty, DBO.position))

# --- Serialize ra file mới ---
g.serialize("ontology/mapping/mapped_players.ttl", format="turtle")
print("Done")



