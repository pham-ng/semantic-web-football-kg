#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate DBpedia mappings for ontology/competition.ttl

- Default MODE = "sub": use rdfs:subClassOf / rdfs:subPropertyOf (khuyên dùng)
- MODE = "equiv": use owl:equivalentClass / owl:equivalentProperty (chỉ khi semantics trùng 100%)

Output: ontology/mapping/map_competition_dbpedia.ttl
"""

from rdflib import Graph, Namespace, RDFS, OWL

# ----- CONFIG -----
INPUT_TTL  = "ontology/competition.ttl"
OUTPUT_TTL = "ontology/mapping/map_competition_dbpedia.ttl"
MODE = "sub"   # "sub" | "equiv"

# ----- NAMESPACES -----
KG     = Namespace("https://kg-football.vn/ontology#")
DBO    = Namespace("http://dbpedia.org/ontology/")
SCHEMA = Namespace("http://schema.org/")
TIME   = Namespace("http://www.w3.org/2006/time#")

# ----- MAPPINGS -----
# Classes in competition.ttl
CLASS_MAPPING = {
    KG.Competition: DBO.SportsTournament,
    KG.League:      DBO.SoccerLeague,
    KG.Cup:         DBO.SportsTournament,
    KG.Tournament:  DBO.SportsTournament,
    KG.Season:      DBO.SoccerLeagueSeason,
    # (Các lớp nền có thể đã nằm ở core, nhưng thêm cũng không sao)
    # KG.AgeGroup, KG.CompetitionType là Enumeration nội bộ → thường không map cứng sang dbo:
}

# Properties in competition.ttl
PROP_MAPPING = {
    # Season relations
    KG.hasSeason:        DBO.season,
    KG.seasonOf:         DBO.season,
    KG.seasonStart:      DBO.startDate,
    KG.seasonEnd:        DBO.endDate,

    # Participation
    KG.participatesIn:   DBO.team,          # light alignment

    # Organization
    KG.organizedBy:      DBO.organiser,
    KG.organizes:        DBO.organiser,

    # Location / attributes
    KG.heldIn:           DBO.country,
    KG.participantCount: DBO.numberOfTeams,
    KG.competitionName:  RDFS.label,        # phụ trợ về tên
}

# ----- MAIN -----
def main():
    g = Graph()
    g.parse(INPUT_TTL, format="turtle")

    # Bind prefixes for nicer TTL
    g.bind("kg", KG)
    g.bind("dbo", DBO)
    g.bind("schema", SCHEMA)
    g.bind("time", TIME)
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

    # Serialize
    g.serialize(OUTPUT_TTL, format="turtle")
    print(f"Done: wrote {OUTPUT_TTL} (mode={MODE})")

if __name__ == "__main__":
    main()
