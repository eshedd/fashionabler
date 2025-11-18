from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
from app.entropy import next_category, get_available_clothes


# --- Database setup ---
Base = declarative_base()
engine = create_engine("sqlite:///app/clothes.db", echo=True)
SessionLocal = sessionmaker(bind=engine)

class StatusEnum(str, enum.Enum):
    clean = "clean"
    # worn = "worn"
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

# allow for persistent sessions
app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def read_clothes(request: Request):
    """Display clothes (rudimentary)"""
    session = SessionLocal()
    clothes = session.query(ClothingItem).all()
    session.close()
    return templates.TemplateResponse("index.html", {"request": request, "clothes": clothes})

@app.get("/select", response_class=HTMLResponse)
def show_candidates(request: Request):
    """Display candidate clothes for selection"""
    session_state = request.session.get("filter_state", {})
    remaining_ids = session_state.get("remaining_ids", None)

    session = SessionLocal()
    if remaining_ids:  # Query only filtered candidates
        print("Showing filtered candidates")
        candidates = session.query(ClothingItem).filter(ClothingItem.id.in_(remaining_ids)).all()
    else:  # Fall back to all clean clothes
        print("Showing all clean candidates")
        candidates = session.query(ClothingItem).filter(ClothingItem.status == StatusEnum.clean).all()
    session.close()

    return templates.TemplateResponse("select.html", {"request": request, "clothes": candidates})

@app.post("/select")
def select_clothing(request: Request, selected_id: int = Form(...)):
    """Mark selected clothing as 'laundry' and clear session state"""
    session = SessionLocal()
    item = session.query(ClothingItem).get(selected_id)
    if item:
        item.status = StatusEnum.laundry
        session.commit()
    session.close()
    if "filter_state" in request.session:  # clear session state
        del request.session["filter_state"]
    return RedirectResponse(url="/select", status_code=303)

@app.get("/choose", response_class=HTMLResponse)
def show_question(request: Request):
    """Show next question to filter clothes"""
    # Load session state
    session_state = request.session.setdefault("filter_state", {
        "remaining_ids": None,  # None means all clothes
        "asked_categories": []
    })

    # Get filtered clothes
    clothes_dicts = get_available_clothes(session_state["remaining_ids"])
    remaining_count = len(clothes_dicts)

    # Determine next category
    asked_categories = set(session_state["asked_categories"])
    category = next_category(clothes_dicts, asked_categories)
    
    # Build options
    options = set()
    for article in clothes_dicts:
        if category in article["tags"]:
            options.update(article["tags"][category])
        
    return templates.TemplateResponse("choose.html", {
        "request": request,
        "category": category,
        "options": options,
        "remaining_count": remaining_count
    })

@app.post("/choose")
def choose_option(request: Request, category: str = Form(...), choice: str = Form(...)):
    """Process user choice and update session state"""
    session_state = request.session.setdefault("filter_state", {
        "remaining_ids": None,
        "asked_categories": []
    })

    # Get filtered clothes
    clothes_dicts = get_available_clothes(session_state["remaining_ids"])
    
    # Filter further based on user choice
    remaining = [
        article for article in clothes_dicts
        if category in article["tags"] \
        and choice in article["tags"][category]
    ]
    
    # Update session
    session_state["remaining_ids"] = [article["id"] for article in remaining]
    session_state["asked_categories"].append(category)
    
    # Stop when few enough remain
    k = 5
    if len(remaining) <= k:
        print("K EXIT")
        return RedirectResponse(url="/select", status_code=303)

    # Stop if all categories have been asked
    all_categories = [set(article["tags"].keys()) for article in remaining]
    all_unique_categories = set().union(*all_categories)
    if len(session_state["asked_categories"]) == len(all_unique_categories):
        print("CATEGORY EXIT")
        return RedirectResponse(url="/select", status_code=303)

    print("CONTINUING")
    return RedirectResponse(url="/choose", status_code=303)

@app.post("/reset")
def reset_questions(request: Request):
    """Reset question session state"""
    request.session["filter_state"] = {
        "asked_categories": [],
        "remaining_ids": None
    }
    return RedirectResponse(url="/choose", status_code=303)

@app.post("/laundry")
def do_laundry():
    """Set all clothes with status 'laundry' back to 'clean'"""
    # Set all clothes with status "laundry" back to "clean"
    session = SessionLocal()
    session.query(ClothingItem).filter(ClothingItem.status == StatusEnum.laundry).update(
        {ClothingItem.status: StatusEnum.clean}
    )
    session.commit()
    session.close()
    return RedirectResponse(url="/select", status_code=303)