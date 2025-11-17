from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum
from fastapi.templating import Jinja2Templates

# --- Database setup ---
Base = declarative_base()
engine = create_engine("sqlite:///app/clothes.db", echo=True)
SessionLocal = sessionmaker(bind=engine)

class StatusEnum(str, enum.Enum):
    clean = "clean"
    worn = "worn"
    laundry = "laundry"

class ClothingItem(Base):
    __tablename__ = "clothes"
    id = Column(Integer, primary_key=True)
    image_path = Column(String, nullable=False)
    tags = Column(String)
    status = Column(Enum(StatusEnum), default=StatusEnum.clean)

Base.metadata.create_all(engine)

# --- FastAPI setup ---
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def read_clothes(request: Request):
    session = SessionLocal()
    clothes = session.query(ClothingItem).all()
    session.close()
    return templates.TemplateResponse("index.html", {"request": request, "clothes": clothes})
