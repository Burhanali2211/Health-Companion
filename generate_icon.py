"""Generate Health Companion app icon PNG (1024x1024) using Pillow."""
from PIL import Image, ImageDraw, ImageFont
import math

SIZE = 1024
FG_SIZE = 768  # foreground (for adaptive icon)

def make_icon(size, bg_color="#1A1A2E", save_path="icon.png", add_bg=True):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if add_bg:
        # Background circle
        draw.ellipse([0, 0, size, size], fill=bg_color)

    cx, cy = size // 2, size // 2
    s = size / 1024  # scale factor

    # Outer ring (saffron glow)
    ring_r = int(420 * s)
    ring_w = int(18 * s)
    draw.ellipse(
        [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
        outline="#E8821A", width=ring_w
    )

    # Inner circle (dal blue, slightly transparent)
    inner_r = int(340 * s)
    draw.ellipse(
        [cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
        fill=(46, 134, 171, 200)
    )

    # Heart shape (health) — drawn as two circles + triangle
    heart_size = int(200 * s)
    hx, hy = cx, cy - int(20 * s)

    # Heart via polygon approximation
    points = []
    for i in range(360):
        angle = math.radians(i)
        # Parametric heart
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        scale = heart_size / 18
        points.append((hx + x * scale, hy + y * scale))

    draw.polygon(points, fill="#F4F1EC")

    # Crescent moon (Kashmiri / Islamic symbol) — top right
    moon_cx = cx + int(200 * s)
    moon_cy = cy - int(200 * s)
    moon_r = int(60 * s)
    # Outer circle
    draw.ellipse(
        [moon_cx - moon_r, moon_cy - moon_r, moon_cx + moon_r, moon_cy + moon_r],
        fill="#D4AC0D"
    )
    # Inner circle to create crescent
    offset = int(20 * s)
    draw.ellipse(
        [moon_cx - moon_r + offset, moon_cy - moon_r,
         moon_cx + moon_r + offset, moon_cy + moon_r],
        fill=bg_color if add_bg else (0, 0, 0, 0)
    )

    # Chinar leaf (simplified 5-point) — bottom
    leaf_cx = cx
    leaf_cy = cy + int(260 * s)
    leaf_r = int(55 * s)
    leaf_pts = []
    for i in range(5):
        angle = math.radians(-90 + i * 72)
        leaf_pts.append((leaf_cx + leaf_r * math.cos(angle), leaf_cy + leaf_r * math.sin(angle)))
        angle2 = math.radians(-90 + i * 72 + 36)
        leaf_pts.append((leaf_cx + (leaf_r * 0.4) * math.cos(angle2), leaf_cy + (leaf_r * 0.4) * math.sin(angle2)))
    draw.polygon(leaf_pts, fill="#C0392B")

    # App name text at bottom — "WS" monogram
    try:
        font_size = int(140 * s)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    text = "ﻭﻁﻥ"  # Watan in Arabic script
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # Center in lower portion — skip if font doesn't render RTL well
    # Instead draw "W S" as monogram
    try:
        font2 = ImageFont.truetype("arial.ttf", int(80 * s))
    except:
        font2 = font
    draw.text((cx, cy + int(80 * s)), "SEHAT", font=font2, fill="#E8821A", anchor="mm")

    img.save(save_path, "PNG")
    print(f"Saved {save_path}")

# Full icon (with background)
make_icon(1024, save_path="F:/watan-sehat/watan_sehat_app/assets/icon/app_icon.png", add_bg=True)

# Foreground only (transparent BG, for adaptive icon)
make_icon(1024, save_path="F:/watan-sehat/watan_sehat_app/assets/icon/app_icon_fg.png", add_bg=False)

print("Icons generated.")
