#!/usr/bin/env python3
"""
Generate PWA icons in multiple sizes
Creates simple colored squares with "T" for Tafsir
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Icon sizes needed for PWA
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Additional sizes for Apple and favicon
ADDITIONAL_SIZES = {
    'apple-touch-icon': 180,
    'favicon-32': 32,
    'favicon-16': 16
}

# Colors
EMERALD = (16, 185, 129)  # #10b981
WHITE = (255, 255, 255)
EMERALD_DARK = (5, 150, 105)  # #059669

def create_icon(size):
    """Create a simple icon with the letter T"""
    # Create image with emerald background
    img = Image.new('RGB', (size, size), EMERALD)
    draw = ImageDraw.Draw(img)

    # Draw white circle
    padding = size // 8
    circle_bbox = [padding, padding, size - padding, size - padding]
    draw.ellipse(circle_bbox, fill=WHITE)

    # Try to use a nice font, fall back to default if not available
    try:
        # Try to find a suitable font
        font_size = int(size * 0.4)
        # This will use default font, but you can specify a path to a TTF file
        font = ImageFont.load_default()
        # For better results, you could use:
        # font = ImageFont.truetype("/path/to/font.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Draw the letter T
    text = "T"
    # Get text bbox for centering (PIL 8.0.0+)
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # Fallback for older PIL versions
        text_width, text_height = draw.textsize(text, font=font)

    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2 - size // 10  # Slightly above center

    # Draw text in emerald color
    draw.text((text_x, text_y), text, fill=EMERALD_DARK, font=font)

    # Add subtle text "تفسير" at bottom if size is large enough
    if size >= 144:
        arabic_text = "تفسير"
        try:
            small_font = ImageFont.load_default()
            arabic_bbox = draw.textbbox((0, 0), arabic_text, font=small_font)
            arabic_width = arabic_bbox[2] - arabic_bbox[0]
        except:
            arabic_width = len(arabic_text) * 8  # Rough estimate

        arabic_x = (size - arabic_width) // 2
        arabic_y = size - padding - 20
        draw.text((arabic_x, arabic_y), arabic_text, fill=EMERALD_DARK, font=small_font)

    return img

def main():
    output_dir = "frontend/public/icons"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating PWA icons in {output_dir}/")

    # Generate standard PWA icons
    for size in SIZES:
        icon = create_icon(size)
        filename = f"icon-{size}x{size}.png"
        filepath = os.path.join(output_dir, filename)
        icon.save(filepath, "PNG", optimize=True)
        print(f"  ✓ Created {filename}")

    # Generate additional icons
    for name, size in ADDITIONAL_SIZES.items():
        icon = create_icon(size)
        if name == 'favicon-32':
            filename = 'favicon-32x32.png'
        elif name == 'favicon-16':
            filename = 'favicon-16x16.png'
        else:
            filename = f"{name}.png"
        filepath = os.path.join(output_dir, filename)
        icon.save(filepath, "PNG", optimize=True)
        print(f"  ✓ Created {filename}")

    # Also save as favicon.ico (multi-resolution)
    icon_16 = create_icon(16)
    icon_32 = create_icon(32)
    favicon_path = os.path.join("frontend/public", "favicon.ico")
    icon_32.save(favicon_path, format='ICO', sizes=[(16, 16), (32, 32)])
    print(f"  ✓ Created favicon.ico")

    print("\n✅ All icons generated successfully!")
    print("\nNext steps:")
    print("1. Icons are ready in frontend/public/icons/")
    print("2. The manifest.json already references these icons")
    print("3. Deploy and test the PWA installation")

if __name__ == "__main__":
    main()