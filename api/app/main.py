from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse, HTMLResponse
from rdflib import Graph
import os

BASE_URI = "https://kg-football.vn/"
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../gold/ttl"))
ONTOLOGY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ontology/core.ttl"))

app = FastAPI(title="KG Football Dereferenceable API")


def load_graph() -> Graph:
	g = Graph()
	if os.path.exists(ONTOLOGY_FILE):
		g.parse(ONTOLOGY_FILE, format="turtle")
	# load gold ttl snippets
	if os.path.isdir(DATA_DIR):
		for fn in os.listdir(DATA_DIR):
			if fn.endswith(".ttl"):
				g.parse(os.path.join(DATA_DIR, fn), format="turtle")
	return g


def negotiate(request: Request) -> str:
	accept = request.headers.get("accept", "")
	if "text/turtle" in accept:
		return "turtle"
	if "application/ld+json" in accept or "application/json" in accept:
		return "json-ld"
	return "html"


@app.get("/resource/{path:path}")
async def deref_resource(path: str, request: Request):
	iri = f"{BASE_URI}resource/{path}"
	fmt = negotiate(request)
	g = load_graph()
	q = f"""
	CONSTRUCT {{ <{iri}> ?p ?o . ?o ?p2 ?o2 }}
	WHERE {{
	  OPTIONAL {{ <{iri}> ?p ?o . OPTIONAL {{ ?o ?p2 ?o2 }} }}
	}}
	"""
	cg = g.query(q).graph
	if len(cg) == 0:
		raise HTTPException(status_code=404, detail="Resource not found")

	if fmt == "turtle":
		return PlainTextResponse(cg.serialize(format="turtle"), media_type="text/turtle")
	if fmt == "json-ld":
		return JSONResponse(content=cg.serialize(format="json-ld", indent=2).decode("utf-8"))

	# HTML view minimal
	triples = "".join([f"<tr><td>{s}</td><td>{p}</td><td>{o}</td></tr>" for s,p,o in cg])
	html = f"""
	<html><head><title>{iri}</title></head>
	<body>
	  <h1>{iri}</h1>
	  <p>Content negotiation: text/turtle, application/ld+json, text/html</p>
	  <table border=\"1\"><thead><tr><th>S</th><th>P</th><th>O</th></tr></thead>
	  <tbody>{triples}</tbody></table>
	</body></html>
	"""
	return HTMLResponse(content=html)


@app.get("/page/resource/{path:path}")
async def human_page(path: str):
	iri = f"{BASE_URI}resource/{path}"
	html = f"""
	<html><head><title>{iri}</title></head>
	<body>
	  <h1>{iri}</h1>
	  <p>Trang mô tả tài nguyên. Vui lòng truy cập <code>/resource/{path}</code> để nhận Turtle/JSON-LD.</p>
	  <p>Ontology: <a href=\"https://kg-football.vn/ontology#\">kg-football.vn/ontology#</a></p>
	</body></html>
	"""
	return HTMLResponse(content=html)
