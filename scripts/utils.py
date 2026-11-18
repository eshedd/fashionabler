from sqlalchemy.orm import sessionmaker
import app.main


def parse_tags(tags):
    if not tags:
        return {}
    out = {}
    for tag in tags:
        try:
            key, value = tag.split(":")
        except:
            key, value = tag, None
        out[key] = out.get(key, []) + [value]
    return out

def get_available_clothes(remaining_ids=None):
    ClothingItem = app.main.ClothingItem
    SessionLocal = sessionmaker(bind=app.main.engine)
    session = SessionLocal()
    query = session.query(ClothingItem)

    if remaining_ids is not None:
        query = query.filter(ClothingItem.id.in_(remaining_ids))

    clothes = [
        {
            "id": article.id,
            "image_path": article.image_path,
            "tags": article.tags.split(",") if article.tags else [],
            "status": article.status.value if article.status else None,
        }
        for article in query.all()
    ]
    session.close()

    for article in clothes:
        parsed = parse_tags(article["tags"])
        article["tags"] = parsed

    uncorrupted = [
        article for article in clothes
        if "corrupted" not in article["tags"] \
        and article["status"] is not None
    ]
    available = [
        article for article in uncorrupted
        if article["status"] != app.main.StatusEnum.laundry.value
    ]
    return available