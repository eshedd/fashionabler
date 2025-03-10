from fashion_clip.fashion_clip import FashionCLIP
import numpy as np
import json
import matplotlib.pyplot as plt
import pandas as pd
import argparse


def encode_text(fclip, text):
    '''
    Encode text using FashionCLIP model

    Args:
        fclip (FashionCLIP): FashionCLIP model
        text (str): text to encode

    Returns:
        text_embedding (np.array): text embedding
    '''
    text_embedding = fclip.encode_text([text], batch_size=1)
    text_embedding /= np.linalg.norm(
        text_embedding, ord=2, axis=-1, keepdims=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Provide prompt.')
    parser.add_argument('prompt', type=str, help='The prompt to encode')
    args = parser.parse_args()

    # load FashionCLIP model
    print('Loading FashionCLIP...')
    fclip = FashionCLIP('fashion-clip')

    # encode text
    text_embedding = encode_text(fclip, args.prompt)

    with open('metadata.json', 'r') as f:
        metadata = json.load(f)
    df = pd.DataFrame(metadata).T

    # calculate similarity
    df['similarity'] = df['embedding'].apply(
        lambda x: np.dot(text_embedding, np.array(x)))
