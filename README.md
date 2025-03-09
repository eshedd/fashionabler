# Fashionabler
A smart clothing recommender for my fashion-incompetent self built with [FashionCLIP](https://github.com/patrickjohncyh/fashion-clip).

## Installation
`pip install -r requirements.txt`

## Notes
- `pip install 'rembg[cpu]'` for using CPU
- Had to downgrade `transformations` library as per this [issue](https://github.com/patrickjohncyh/fashion-clip/issues/39#issuecomment-2506391126)
- FYI: FashionCLIP has a limit of 77 tokens, so keep the prompt to less than that.
