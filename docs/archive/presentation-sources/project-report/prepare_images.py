from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'images'
OUT.mkdir(parents=True, exist_ok=True)

# Crop the existing demonstration captures, retaining the relevant UI evidence.
REGIONS = {
    'home': ('docs/assets/demo-03.png', (260, 60, 1920, 710)),
    'patient': ('docs/assets/demo-04.png', (280, 70, 1900, 390)),
    'record': ('docs/assets/demo-05.png', (285, 75, 1900, 380)),
    'protection': ('docs/assets/demo-protection.png', (290, 0, 1900, 365)),
    'upload': ('tmp/presentation/upload.png', (640, 130, 1280, 670)),
    'answer': ('docs/assets/demo-08.png', (355, 240, 1055, 455)),
    'boundary': ('docs/assets/demo-09.png', (300, 240, 1570, 420)),
}

for name, (source, bounds) in REGIONS.items():
    with Image.open(ROOT / source) as image:
        image.crop(bounds).save(OUT / f'{name}.png')

print(f'Prepared {len(REGIONS)} source crops in {OUT}')
