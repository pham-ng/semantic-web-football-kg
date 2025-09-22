#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate DBpedia mappings for ontology/core.ttl

- MODE = "sub"   -> rdfs:subClassOf / rdfs:subPropertyOf  (khuyên dùng, an toàn)
- MODE = "equiv" -> owl:equivalentClass / owl:equivalentProperty (chỉ khi semantics trùng 100%)

Output: ontology/mapping/map_core_dbpedia.ttl
"""

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
    KG.City:         DBO.Place,        # DBpedia không có dbo:City -> dùng Place/Settlement
    # positions
    KG.Position:     DBO.Position,     # lớp tổng quát Position
    # (Các subclass như Goalkeeper/Defender/Midfielder/Forward giữ internal; nếu muốn link thêm
    # thì dùng SKOS exactMatch tới dbr:* ở một file mapping khác như đã trao đổi)
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

    # (schema:name thường dùng sẵn, không map lại)
}

def main():
    g = Graph()
    g.parse(INPUT_TTL, format="turtle")

    # Bind prefixes for nicer TTL
    g.bind("kg", KG)
    g.bind("dbo", DBO)
    g.bind("schema", SCM)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)

    # Add class mappings
    for kg_cls, dbo_cls in CLASS_MAPPING.items():
        if MODE == "equiv":
            g.add((kg_cls, OWL.equivalentClass, dbo_cls))
        else:
            g.add((kg_cls, RDFS.subClassOf, dbo_cls))

    # Add property mappings
    for kg_prop, dbo_prop in PROP_MAPPING.items():
        if MODE == "equiv":
            g.add((kg_prop, OWL.equivalentProperty, dbo_prop))
        else:
            g.add((kg_prop, RDFS.subPropertyOf, dbo_prop))

    g.serialize(OUTPUT_TTL, format="turtle")
    print(f"Done: wrote {OUTPUT_TTL} (mode={MODE})")

if __name__ == "__main__":
    main()
