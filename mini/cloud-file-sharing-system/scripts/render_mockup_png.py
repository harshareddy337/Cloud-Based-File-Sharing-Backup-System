from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'static' / 'images' / 'screenshot@2x.png'
W, H = 2400, 1400
img = Image.new('RGB', (W, H), '#f7fbfe')
d = ImageDraw.Draw(img)

# simple gradient background
for i in range(H):
    t = i / H
    r = int(247*(1-t) + 238*t)
    g = int(251*(1-t) + 246*t)
    b = int(254*(1-t) + 251*t)
    d.line([(0,i),(W,i)], fill=(r,g,b))

# header rectangle
hdr_x, hdr_y, hdr_w, hdr_h = 80, 60, W-160, 140
d.rounded_rectangle([hdr_x,hdr_y,hdr_x+hdr_w,hdr_y+hdr_h], radius=20, fill='#ffffff')

# title
try:
    font_large = ImageFont.truetype('Segoe UI.ttf', 64)
    font_med = ImageFont.truetype('Segoe UI.ttf', 36)
    font_sm = ImageFont.truetype('Segoe UI.ttf', 28)
except Exception:
    font_large = ImageFont.load_default()
    font_med = ImageFont.load_default()
    font_sm = ImageFont.load_default()

d.text((120, hdr_y+48), 'Cloud Share', fill=(43,108,176), font=font_large)

# left panel
left_x, left_y = 80, 260
left_w, left_h = int((W-240)*0.63), H-360
d.rounded_rectangle([left_x,left_y,left_x+left_w,left_y+left_h], radius=20, fill='#ffffff')

# upload box
up_x, up_y = left_x+40, left_y+36
up_w, up_h = left_w-80, 120
d.rounded_rectangle([up_x,up_y,up_x+up_w,up_y+up_h], radius=14, fill='#f4f8fb')
d.text((up_x+24, up_y+28), 'Choose file...', fill=(108,117,125), font=font_med)
# upload button
btn_x = up_x + up_w - 240
d.rounded_rectangle([btn_x, up_y+12, btn_x+200, up_y+up_h-12], radius=12, fill='#3498db')
d.text((btn_x+36, up_y+32), 'Upload', fill=(255,255,255), font=font_med)

# files list area
files_y = up_y + up_h + 40
for i in range(3):
    ry = files_y + i*116
    d.rounded_rectangle([up_x, ry, up_x+up_w, ry+96], radius=12, fill='#fbfdff')
    d.rectangle([up_x+12, ry+12, up_x+92, ry+84], fill='#eef6fb')
    d.text((up_x+120, ry+30), f'hello_{i+1}.txt', fill=(32,54,71), font=font_med)
    d.text((up_x+120, ry+60), '1.2 KB • text', fill=(108,117,125), font=font_sm)
    d.text((up_x+up_w-160, ry+36), 'Download', fill=(32,54,71), font=font_med)

# right panel
r_x = left_x + left_w + 40
r_w = W - r_x - 80
d.rounded_rectangle([r_x, left_y, r_x+r_w, left_y+left_h], radius=20, fill='#ffffff')
d.text((r_x+30, left_y+36), 'Account', fill=(32,54,71), font=font_med)
d.text((r_x+30, left_y+76), 'smoke_test@example.com', fill=(108,117,125), font=font_sm)

# footer tag
# save
OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print('Wrote', OUT)
