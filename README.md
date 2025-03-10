# Fashionabler 👖
A smart clothing recommender for my fashion-incompetent self built with [FashionCLIP](https://github.com/patrickjohncyh/fashion-clip).

## Installation
`pip install -r requirements.txt`
### M1 Mac
- `pip install 'rembg[cpu]'` for using CPU
- Downgrade to `transformations==4.42.4` (see [issue](https://github.com/patrickjohncyh/fashion-clip/issues/39#issuecomment-2506391126))

## Notes
- FashionCLIP has a limit of 77 tokens, so keep the prompt to less than that

### TODO
- [ ] Use weather report and emotion prediction for informing outfit
- [ ] Add laundry (i.e. remove worn clothes from recommendation)
- [ ] Generative try-on (VTON) feature
- [ ] Track clothing article usage frequency

### Further Reading
- [FashionCLIP](https://www.nature.com/articles/s41598-022-23052-9) ([github](https://github.com/patrickjohncyh/fashion-clip))
    - Might replace with [Marqo-FashionLCIP](https://github.com/marqo-ai/marqo-FashionCLIP)
- [Outfit Transformer](https://arxiv.org/pdf/2204.04812) ([github](https://github.com/owj0421/outfit-transformer))
- [VTON Research](https://github.com/minar09/awesome-virtual-try-on?tab=readme-ov-file#Image-based-2D-Virtual-Try-on)
