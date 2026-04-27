import os
from pathlib import Path
import sys

try:
    import cairosvg
except Exception as e:
    print('CairoSVG is not installed:', e)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / 'static' / 'images' / 'screenshot.svg'
OUT = ROOT / 'static' / 'images' / 'screenshot@2x.png'

if not SVG.exists():
    print('SVG not found at', SVG)
    sys.exit(1)

print('Rendering', SVG, '->', OUT)
# Render at a larger width for high-res (2x)
try:
    # Try to set output_width to double the original viewBox width (1200 -> 2400)
    cairosvg.svg2png(url=str(SVG), write_to=str(OUT), output_width=2400)
    print('Wrote', OUT)
except Exception as e:
    print('Conversion failed:', e)
    sys.exit(3)
