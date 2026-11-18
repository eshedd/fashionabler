"""Rank saved FastFit outfits against a free-text prompt with FashionCLIP."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import numpy as np
from fashion_clip.fashion_clip import FashionCLIP


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = PROJECT_ROOT / "imgs"
_SEGMENTED_DIR = IMAGE_ROOT / "segmented"
GARMENT_DIR = _SEGMENTED_DIR if _SEGMENTED_DIR.is_dir() else IMAGE_ROOT
METADATA_PATH = PROJECT_ROOT / "imgs" / "metadata.json"
_FASTFIT_DEFAULT = PROJECT_ROOT / "fastfit_output"
_FASTFIT_50 = PROJECT_ROOT / "fastfit_output_50"
FASTFIT_DIR = _FASTFIT_DEFAULT if _FASTFIT_DEFAULT.is_dir() else _FASTFIT_50
REPORT_DIR = PROJECT_ROOT / "recommendations"
TOP_TYPES = {"tshirt", "longshirt", "sweatshirt"}
BOTTOM_TYPES = {"pants", "shorts"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def normalize(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = np.linalg.norm(vector)
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("FashionCLIP returned an invalid zero-length embedding.")
    return vector / norm


def metadata_entry_for(metadata: dict, image_path: Path) -> tuple[str, dict]:
    key = image_path.relative_to(PROJECT_ROOT).as_posix()
    if key in metadata:
        entry = metadata[key]
        return key, entry if isinstance(entry, dict) else {}

    # Older metadata may retain the prior imgs/segmented/<name> key after
    # garment files have been flattened into imgs/.
    for saved_key, entry in metadata.items():
        if Path(saved_key).name == image_path.name and isinstance(entry, dict):
            return saved_key, entry
    return key, {}


def load_metadata() -> dict:
    if not METADATA_PATH.is_file():
        return {}
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read {METADATA_PATH}: {exc}") from exc


def save_metadata(metadata: dict) -> None:
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = METADATA_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, METADATA_PATH)


def ensure_image_embeddings(
    fclip: FashionCLIP, metadata: dict, image_paths: list[Path], rebuild: bool
) -> dict[str, np.ndarray]:
    embeddings: dict[str, np.ndarray] = {}
    missing: list[Path] = []

    for image_path in image_paths:
        _, entry = metadata_entry_for(metadata, image_path)
        vector = entry.get("embedding") if isinstance(entry, dict) else None
        if not rebuild and vector is not None:
            try:
                embeddings[image_path.stem] = normalize(np.asarray(vector))
                continue
            except (TypeError, ValueError):
                pass
        missing.append(image_path)

    if missing:
        print(f"Encoding {len(missing)} garment image(s)...", flush=True)
        raw_vectors = np.asarray(
            fclip.encode_images([str(path) for path in missing], batch_size=32)
        )
        if raw_vectors.ndim != 2 or raw_vectors.shape[0] != len(missing):
            raise ValueError(
                "FashionCLIP returned an unexpected image embedding shape: "
                f"{raw_vectors.shape}"
            )

        for image_path, vector in zip(missing, raw_vectors):
            key, entry = metadata_entry_for(metadata, image_path)
            if not isinstance(entry, dict):
                entry = {}
            entry["articleType"] = image_path.stem.rsplit("_", 1)[-1]
            entry["embedding"] = normalize(vector).tolist()
            metadata[key] = entry
            embeddings[image_path.stem] = normalize(vector)

        save_metadata(metadata)
        print(f"Updated embedding cache: {METADATA_PATH}", flush=True)
    else:
        print(f"Using cached embeddings for {len(embeddings)} garments.", flush=True)

    return embeddings


def prompt_embedding(fclip: FashionCLIP, prompt: str) -> np.ndarray:
    vector = fclip.encode_text([prompt], batch_size=1)
    return normalize(np.asarray(vector)[0])


def rank_outfits(
    prompt_vector: np.ndarray,
    embeddings: dict[str, np.ndarray],
    metadata: dict,
) -> tuple[list[dict], int]:
    tops: list[tuple[str, np.ndarray]] = []
    bottoms: list[tuple[str, np.ndarray]] = []

    for key, entry in metadata.items():
        if not isinstance(entry, dict):
            continue
        image_id = Path(key).stem
        image_vector = embeddings.get(image_id)
        if image_vector is None:
            continue
        garment_type = str(entry.get("articleType", image_id.rsplit("_", 1)[-1])).lower()
        if garment_type in TOP_TYPES:
            tops.append((image_id, image_vector))
        elif garment_type in BOTTOM_TYPES:
            bottoms.append((image_id, image_vector))

    outfits: list[dict] = []
    missing_images = 0
    for top_id, top_vector in tops:
        for bottom_id, bottom_vector in bottoms:
            output_path = FASTFIT_DIR / f"{top_id}__{bottom_id}.png"
            if not output_path.is_file():
                missing_images += 1
                continue

            top_prompt_match = float(np.dot(top_vector, prompt_vector))
            bottom_prompt_match = float(np.dot(bottom_vector, prompt_vector))
            prompt_match = (top_prompt_match + bottom_prompt_match) / 2
            cohesion = float(np.dot(top_vector, bottom_vector))
            outfits.append({
                "top_id": top_id,
                "bottom_id": bottom_id,
                "top_prompt_match": top_prompt_match,
                "bottom_prompt_match": bottom_prompt_match,
                "prompt_match": prompt_match,
                "cohesion": cohesion,
                "score": prompt_match,
                "output_path": output_path,
            })

    # Prompt and image-image cosine similarities have different raw ranges.
    # Use prompt match as the ranking score; use cohesion only to break ties.
    outfits.sort(
        key=lambda item: (item["prompt_match"], item["cohesion"]),
        reverse=True,
    )
    return outfits, missing_images


def local_image_url(path: Path) -> str:
    relative = os.path.relpath(path, REPORT_DIR)
    return quote(Path(relative).as_posix(), safe="/._-")


def write_report(prompt: str, outfits: list[dict], top_k: int) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "latest.html"
    cards = []

    for rank, outfit in enumerate(outfits[:top_k], start=1):
        top_path = GARMENT_DIR / f"{outfit['top_id']}.jpg"
        bottom_path = GARMENT_DIR / f"{outfit['bottom_id']}.jpg"
        top_name = html.escape(outfit["top_id"])
        bottom_name = html.escape(outfit["bottom_id"])
        cards.append(f"""
        <article class="card">
          <div class="rank">#{rank}</div>
          <img class="tryon" src="{html.escape(local_image_url(outfit['output_path']), quote=True)}" alt="Try-on result for {top_name} and {bottom_name}">
          <div class="garments">
            <figure><img src="{html.escape(local_image_url(top_path), quote=True)}" alt="Top {top_name}"><figcaption>{top_name}</figcaption></figure>
            <figure><img src="{html.escape(local_image_url(bottom_path), quote=True)}" alt="Bottom {bottom_name}"><figcaption>{bottom_name}</figcaption></figure>
          </div>
          <p class="scores">Prompt match {outfit['prompt_match']:.3f} · Top {outfit['top_prompt_match']:.3f} · Bottom {outfit['bottom_prompt_match']:.3f} · Pair cohesion {outfit['cohesion']:.3f}</p>
        </article>
        """)

    prompt_text = html.escape(prompt)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fashionabler recommendations</title>
  <style>
    :root {{ color-scheme: light; --ink:#20231f; --muted:#73786f; --paper:#f5f3ee; --card:#fff; --accent:#596b4d; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; background:var(--paper); color:var(--ink); font:16px/1.45 system-ui,-apple-system,sans-serif; }}
    main {{ max-width:1280px; margin:auto; padding:36px 22px 60px; }}
    h1 {{ margin:0 0 8px; font:500 clamp(2rem,5vw,3.4rem)/1.05 Georgia,serif; }}
    .prompt {{ margin:0 0 6px; font-size:1.2rem; }} .meta {{ color:var(--muted); margin:0 0 28px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr)); gap:20px; }}
    .card {{ position:relative; background:var(--card); padding:14px; border-radius:14px; box-shadow:0 5px 22px #292b2410; }}
    .rank {{ position:absolute; top:22px; left:22px; z-index:1; background:#fffE; color:var(--accent); padding:5px 10px; border-radius:99px; font-weight:700; }}
    .tryon {{ display:block; width:100%; aspect-ratio:3/4; object-fit:contain; background:#eae9e3; border-radius:9px; }}
    .garments {{ display:flex; gap:12px; margin-top:12px; }} figure {{ width:50%; margin:0; min-width:0; }}
    figure img {{ display:block; width:100%; height:150px; object-fit:contain; background:#f4f3ef; border-radius:8px; }}
    figcaption {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--muted); font-size:.8rem; margin-top:5px; }}
    .scores {{ color:var(--muted); font-size:.84rem; margin:12px 2px 2px; }}
  </style>
</head>
<body><main>
  <h1>Wardrobe matches</h1>
  <p class="prompt">“{prompt_text}”</p>
  <p class="meta">Top {min(top_k, len(outfits))} of {len(outfits)} available outfits · ranked by prompt match; pair cohesion breaks ties · {timestamp}</p>
  <section class="grid">{''.join(cards)}</section>
</main></body></html>
"""
    temporary = report_path.with_suffix(".html.tmp")
    temporary.write_text(document, encoding="utf-8")
    os.replace(temporary, report_path)
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rank existing FastFit outfit images against a FashionCLIP text prompt."
    )
    parser.add_argument("prompt", help="short natural-language outfit prompt")
    parser.add_argument("--top-k", type=int, default=10, help="number of results to show")
    parser.add_argument(
        "--rebuild-embeddings", action="store_true",
        help="re-encode all wardrobe images instead of reusing the saved cache",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.top_k < 1:
        print("--top-k must be at least 1.", file=sys.stderr)
        return 2
    image_paths = sorted(
        path for path in GARMENT_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ) if GARMENT_DIR.is_dir() else []
    if not image_paths:
        print(f"No garment images found in {GARMENT_DIR}.", file=sys.stderr)
        return 2
    if not FASTFIT_DIR.is_dir():
        print(f"FastFit results directory does not exist: {FASTFIT_DIR}", file=sys.stderr)
        return 2

    try:
        metadata = load_metadata()
        print("Loading FashionCLIP...", flush=True)
        fclip = FashionCLIP("fashion-clip")
        embeddings = ensure_image_embeddings(
            fclip, metadata, image_paths, args.rebuild_embeddings
        )
        query_vector = prompt_embedding(fclip, args.prompt)
    except Exception as exc:
        print(f"Could not prepare FashionCLIP embeddings: {exc}", file=sys.stderr)
        return 1

    outfits, missing_images = rank_outfits(query_vector, embeddings, metadata)
    if not outfits:
        print("No outfits with matching garment embeddings and FastFit images were found.", file=sys.stderr)
        return 1

    print(f"Ranked {len(outfits)} available outfits for: {args.prompt!r}")
    for rank, outfit in enumerate(outfits[:args.top_k], start=1):
        print(
            f"{rank:>2}. {outfit['top_id']} + {outfit['bottom_id']}  "
            f"score={outfit['score']:.3f} "
            f"(top={outfit['top_prompt_match']:.3f}, "
            f"bottom={outfit['bottom_prompt_match']:.3f}, "
            f"cohesion={outfit['cohesion']:.3f})  "
            f"{outfit['output_path'].relative_to(PROJECT_ROOT)}"
        )

    report_path = write_report(args.prompt, outfits, args.top_k)
    print(f"HTML preview: {report_path}")
    if missing_images:
        print(f"Skipped {missing_images} garment combinations without a FastFit output image.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
