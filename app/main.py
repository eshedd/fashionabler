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
from pathlib import Path
from scripts.entropy import next_category
from scripts.utils import get_available_clothes
from scripts import recommend


# --- Project paths and database setup ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = PROJECT_ROOT / "imgs"
DATABASE_PATH = Path(__file__).resolve().parent / "clothes.db"
Base = declarative_base()
engine = create_engine(f"sqlite:///{DATABASE_PATH.as_posix()}", echo=False)
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

    def __init__(self, image_path, tags="", status=StatusEnum.clean, id=None):
        self.image_path = image_path
        self.tags = tags
        self.status = status
        if id is not None:
            self.id = id
        else:
            try:
                self.id = int(Path(image_path).stem.split("_", 1)[0])
            except ValueError:
                # Let SQLite allocate an ID for filenames without a numeric prefix.
                pass

Base.metadata.create_all(engine)


def seed_wardrobe_from_images():
    """Add indexed imgs/ garments to the local wardrobe database once."""
    session = SessionLocal()
    try:
        for image_path in sorted(IMAGE_DIR.glob("*.jpg")):
            try:
                image_id = int(image_path.stem.split("_", 1)[0])
            except ValueError:
                continue

            exists = session.query(ClothingItem).filter_by(id=image_id).first()
            if exists is None:
                garment_type = image_path.stem.rsplit("_", 1)[-1]
                session.add(ClothingItem(
                    id=image_id,
                    image_path=image_path.name,
                    tags=f"article_type:{garment_type}",
                    status=StatusEnum.clean,
                ))
        session.commit()
    finally:
        session.close()


seed_wardrobe_from_images()

# --- FastAPI setup ---
app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/imgs", StaticFiles(directory=str(IMAGE_DIR)), name="wardrobe_images")
app.mount("/fastfit", StaticFiles(directory=str(recommend.FASTFIT_DIR)), name="fastfit_images")

# allow for persistent sessions
app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def read_clothes(request: Request):
    """Display clothes (rudimentary)"""
    session = SessionLocal()
    clothes = session.query(ClothingItem).all()
    session.close()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "clothes": clothes},
    )

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

    return templates.TemplateResponse(
        request=request,
        name="select.html",
        context={"request": request, "clothes": candidates},
    )

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
        
    return templates.TemplateResponse(
        request=request,
        name="choose.html",
        context={
            "request": request,
            "category": category,
            "options": options,
            "remaining_count": remaining_count,
        },
    )

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

_fashion_clip = None
_garment_embeddings = None


@app.api_route("/outfit", methods=["GET", "POST"], response_class=HTMLResponse)
def prompt_search(request: Request, prompt: str = Form(default="")):
    session_state = request.session.get("filter_state", {})
    remaining_ids = session_state.get("remaining_ids", None)
    matches = []
    error = None

    if request.method == "POST" and prompt.strip():
        global _fashion_clip, _garment_embeddings
        try:
            image_paths = sorted(
                path for path in recommend.GARMENT_DIR.iterdir()
                if path.is_file() and path.suffix.lower() in recommend.IMAGE_EXTENSIONS
            )
            if _fashion_clip is None:
                _fashion_clip = recommend.FashionCLIP("fashion-clip")
            metadata = recommend.load_metadata()
            _garment_embeddings = recommend.ensure_image_embeddings(
                _fashion_clip, metadata, image_paths, rebuild=False
            )
            query = recommend.prompt_embedding(_fashion_clip, prompt.strip())
            matches, _ = recommend.rank_outfits(query, _garment_embeddings, metadata)

            available_stems = {
                Path(item["image_path"]).stem
                for item in get_available_clothes(remaining_ids)
            }
            matches = [
                item for item in matches
                if item["top_id"] in available_stems
                and item["bottom_id"] in available_stems
            ][:10]
            for item in matches:
                item["image_url"] = f"/fastfit/{item['output_path'].name}"
                top_image = recommend.GARMENT_DIR / (item["top_id"] + ".jpg")
                bottom_image = recommend.GARMENT_DIR / (item["bottom_id"] + ".jpg")
                item["top_image_url"] = f"/imgs/{top_image.relative_to(IMAGE_DIR)}"
                item["bottom_image_url"] = f"/imgs/{bottom_image.relative_to(IMAGE_DIR)}"
        except Exception as exc:
            error = f"Could not search outfits: {exc}"

    return templates.TemplateResponse(
        request=request,
        name="outfit.html",
        context={"request": request, "prompt": prompt, "matches": matches, "error": error},
    )
