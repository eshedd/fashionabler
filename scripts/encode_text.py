from fashion_clip.fashion_clip import FashionCLIP
import numpy as np
import json
import matplotlib.pyplot as plt
import pandas as pd
import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def encode_text(text):
    fclip = FashionCLIP('fashion-clip')
    text_embedding = fclip.encode_text([text], batch_size=1)
    text_embedding /= np.linalg.norm(
        text_embedding, ord=2, axis=-1, keepdims=True)
    return text_embedding

def prompt_outfit(prompt):
    text_embed = encode_text(prompt)
    metadata_path = PROJECT_ROOT / 'imgs' / 'metadata.json'
    with metadata_path.open('r', encoding='utf-8') as f:
        img_embeds = json.load(f)

    img_ids = []
    similarities = []
    for img_path, data in img_embeds.items():
        img_embed = np.array(data['embedding']).reshape(1, -1)
        similarity = np.dot(text_embed, img_embed.T).squeeze()
        img_id = int(Path(img_path).stem.split("_", 1)[0])
        img_ids.append(img_id)
        similarities.append(similarity)
    img_ids, similarities = zip(*sorted(
        zip(img_ids, similarities), key=lambda x: x[1], reverse=True))
    k = 5
    return img_ids[:k], similarities[:k]
