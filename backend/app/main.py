from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import LineString
from app.config import settings
from app.models import POI, Trajectory
import joblib
import jieba

app = FastAPI(title="City POI Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine(settings.database_url)

def get_db():
    with Session(engine) as session:
        yield session

clf_pipeline = None

def get_classifier():
    global clf_pipeline
    if clf_pipeline is None:
        try:
            clf_pipeline = joblib.load("/app/app/poi_classifier.pkl")
        except FileNotFoundError:
            return None
    return clf_pipeline

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/api/pois")
def list_pois(
    db: Session = Depends(get_db),
    category: str = Query(None),
    limit: int = Query(500, le=2000),
    offset: int = Query(0),
):
    query = db.query(POI)
    if category:
        query = query.filter(POI.category == category)
    pois = query.offset(offset).limit(limit).all()
    features = []
    for poi in pois:
        point = to_shape(poi.geom)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [point.x, point.y]},
            "properties": {
                "id": poi.id,
                "name": poi.name,
                "category": poi.category,
                "address": poi.address,
                "description": poi.description,
            }
        })
    return {
        "type": "FeatureCollection",
        "total": query.count(),
        "features": features
    }

@app.get("/api/pois/categories")
def list_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        text("SELECT category, COUNT(*) as cnt FROM pois GROUP BY category ORDER BY cnt DESC")
    ).fetchall()
    return [{"category": r[0], "count": r[1]} for r in rows]

@app.get("/api/trajectories")
def list_trajectories(db: Session = Depends(get_db)):
    trajectories = db.query(Trajectory).all()
    features = []
    for t in trajectories:
        line = to_shape(t.geom)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": list(line.coords)},
            "properties": {"id": t.id, "name": t.name}
        })
    return {"type": "FeatureCollection", "features": features}

@app.post("/api/trajectories")
def create_trajectory(name: str, coords: list[list[float]], db: Session = Depends(get_db)):
    t = Trajectory(name=name, geom=from_shape(LineString(coords), srid=4326))
    db.add(t)
    db.commit()
    return {"id": t.id, "name": t.name}

@app.get("/api/classify")
def classify_poi(name: str, description: str = ""):
    clf = get_classifier()
    if clf is None:
        return {"error": "模型未找到"}
    text_input = " ".join(jieba.cut(name + " " + description))
    category = clf.predict([text_input])[0]
    proba = clf.predict_proba([text_input])[0]
    confidence = round(float(max(proba)), 3)
    return {"name": name, "category": category, "confidence": confidence}