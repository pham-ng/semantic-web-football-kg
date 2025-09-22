from rdflib import Graph, Namespace, RDFS, OWL

# ----- CONFIG -----
INPUT_TTL  = "ontology/core.ttl"
OUTPUT_TTL = "ontology/mapping/map_core_dbpedia.ttl"
MODE = "sub"   # "sub" | "equiv"

# ----- NAMESPACES -----
KG   = Namespace("https://kg-football.vn/ontology#")
DBO  = Namespace("http://dbpedia.org/ontology/")
SCM  = Namespace("http://schema.org/")

# ----- CLASS MAPPING -----
CLASS_MAPPING = {
    # Core domain classes
    KG.Player:       DBO.SoccerPlayer,
    KG.Team:         DBO.SportsTeam,
    KG.Club:         DBO.SoccerClub,
    KG.NationalTeam: DBO.SportsTeam,
    KG.Match:        DBO.SoccerMatch,
    KG.Stadium:      DBO.Stadium,
    # geography (nếu core.ttl có)
    KG.Country:      DBO.Country,
    KG.City:         DBO.Place,        
    # positions
    KG.Position:     DBO.Position,     

}

# ----- PROPERTY MAPPING -----
PROP_MAPPING = {
    # Player
    KG.playsFor:        DBO.team,
    KG.primaryPosition: DBO.position,
    KG.birthDate:       DBO.birthDate,
    KG.shirtNumber:     DBO.number,
    KG.nationality:     DBO.nationality,
    KG.height:          DBO.height,
    KG.weight:          DBO.weight,
    # optional nếu có trong core.ttl
    KG.birthPlace:      DBO.birthPlace,
    KG.secondaryPosition: DBO.position,

    # Match
    KG.homeTeam:        DBO.homeTeam,
    KG.awayTeam:        DBO.awayTeam,
    KG.venue:           DBO.location,
    KG.kickoffTime:     DBO.time,
    KG.attendance:      DBO.attendance,

    # Team/Club/Stadium
    KG.hasCoach:        DBO.coach,
    KG.homeStadium:     DBO.ground,
    KG.locatedIn:       DBO.location,
    KG.capacity:        DBO.capacity,


}
