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
