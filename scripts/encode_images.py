import glob
from fashion_clip.fashion_clip import FashionCLIP
import numpy as np
import json
import argparse


def encode_images(fclip, image_dir, batch_size):
    '''
    Encode images using FashionCLIP model

    Args:
        fclip (FashionCLIP): FashionCLIP model
        image_dir (str): directory of images to encode
        batch_size (int): batch size for encoding

    Returns:
        images (list): list of image paths
        image_embeddings (np.array): image embeddings
    '''
    print('encoding images...')
    images = glob.glob(image_dir + '/*')
    image_embeddings = fclip.encode_images(images, batch_size=batch_size)

    # normalize to unit norm to use dot product instead of cosine similarity
    image_embeddings /= np.linalg.norm(
        image_embeddings, ord=2, axis=-1, keepdims=True)

    return images, image_embeddings


def save_embeddings(images, embeddings):
    '''
    Save image embeddings to json file

    Args:
        images (list): list of image paths
        embeddings (np.array): image embeddings
    '''
    with open('metadata.json', 'r+') as f:
        metadata = json.load(f)
        for idx, image in enumerate(images):
            try:
                metadata[image]['embedding'] = embeddings[idx].tolist()
            except KeyError:
                metadata[image] = {
                    'embedding': embeddings[idx].tolist()
                }
        f.seek(0)
        json.dump(metadata, f, indent=4)
        f.truncate()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='args for encoding images')
    parser.add_argument(
        '--dir',
        type=str,
        help='directory of images to encode',
        default='imgs/segmented'
    )
    parser.add_argument(
        '--batch',
        type=int,
        help='batch size',
        default=32
    )
    args = parser.parse_args()

    # load FashionCLIP model
    print('loading FashionCLIP...')
    fclip = FashionCLIP('fashion-clip')

    images, image_embeddings = encode_images(fclip, args.dir, args.batch)
    save_embeddings(images, image_embeddings)
