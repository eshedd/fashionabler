# Fashionabler 👖
A smart clothing recommender for my fashion-incompetent self built with [FashionCLIP](https://github.com/patrickjohncyh/fashion-clip).

## Installation
`pip install -r requirements.txt`

`huggingface_hub==0.27.0`

### M1 Mac
- `pip install 'rembg[cpu]'` for using CPU
- Downgrade to `transformations==4.42.4` (see [issue](https://github.com/patrickjohncyh/fashion-clip/issues/39#issuecomment-2506391126))

## Notes
- FashionCLIP has a limit of 77 tokens, so keep the prompt to less than that
- Details from FashionCLIP finetuning on Farfetch dataset ([unreleased](https://github.com/patrickjohncyh/fashion-clip/issues/1))
    - Dataset has mostly long captions --> longer prompts may be more effective
    - Biased towards standard product images, i.e. centered on white background

### TODO
- [ ] Generative try-on (VTON) feature --> [CatVTON](https://arxiv.org/pdf/2407.15886) ([github](https://github.com/Zheng-Chong/CatVTON))
- [ ] Cache previously generated images to reduce inference frequency
- [ ] Intuitive UI for entering prompt + visualizing outfits
- [ ] Track clothing article usage frequency
- [ ] Add laundry (i.e. remove worn clothes from recommendation)
- [ ] Use weather report and emotion prediction for informing outfit ([GradedRec](https://arxiv.org/pdf/2204.02473) for reference on traversing FashionCLIP latent space)

### Further Reading
- [FashionCLIP](https://www.nature.com/articles/s41598-022-23052-9) ([github](https://github.com/patrickjohncyh/fashion-clip))
    - Might replace with [Marqo-FashionLCIP](https://github.com/marqo-ai/marqo-FashionCLIP)
- [Outfit Transformer](https://arxiv.org/pdf/2204.04812) ([github](https://github.com/owj0421/outfit-transformer))
- [VTON Research List 1](https://github.com/minar09/awesome-virtual-try-on?tab=readme-ov-file#Image-based-2D-Virtual-Try-on) and [VTON Research List 2](https://github.com/Zheng-Chong/Awesome-Try-On-Models?tab=readme-ov-file)

