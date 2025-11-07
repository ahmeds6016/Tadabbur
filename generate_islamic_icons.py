#!/usr/bin/env python3
"""
Generate PWA icons with Islamic design theme
Matches the Tafsir Simplified brand colors
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# Icon sizes needed for PWA
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Additional sizes for Apple and favicon
ADDITIONAL_SIZES = {
    'apple-touch-icon': 180,
    'favicon-32': 32,
    'favicon-16': 16
}

# Islamic Design System Colors (from globals.css)
TEAL = (13, 148, 136)      # #0D9488 - Primary
TEAL_DARK = (15, 118, 110)  # #0F766E
GOLD = (212, 175, 55)        # #D4AF37 - Gold accent
GOLD_LIGHT = (244, 228, 193) # #F4E4C1
DEEP_BLUE = (30, 58, 95)     # #1E3A5F - Deep blue
CREAM = (253, 251, 247)      # #FDFBF7 - Background

def create_islamic_icon(size):
    """Create an icon with Islamic geometric design and Arabic text"""
    # Create image with cream background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Create gradient-like effect with circles
    center = size // 2

    # Outer circle - Deep Blue
    draw.ellipse([0, 0, size, size], fill=DEEP_BLUE)

    # Middle circle - Teal gradient effect
    padding = size // 16
    draw.ellipse([padding, padding, size-padding, size-padding], fill=TEAL)

    # Inner decorative circle - slightly smaller
    inner_padding = size // 8
    draw.ellipse([inner_padding, inner_padding, size-inner_padding, size-inner_padding],
                 fill=TEAL_DARK)

    # Gold accent ring
    gold_padding = int(size * 0.15)
    draw.ellipse([gold_padding, gold_padding, size-gold_padding, size-gold_padding],
                 outline=GOLD, width=max(2, size//64))

    # White background circle for text
    text_padding = int(size * 0.2)
    draw.ellipse([text_padding, text_padding, size-text_padding, size-text_padding],
                 fill=CREAM)

    # Draw Arabic text "ت" (first letter of تفسير - Tafsir)
    # This represents the Tafsir concept
    try:
        # Try to use a better font if available
        font_size = int(size * 0.35)
        font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    # Main Arabic letter ت
    arabic_letter = "ت"

    # Calculate position for centering
    try:
        bbox = draw.textbbox((0, 0), arabic_letter, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # Fallback for older PIL
        text_width = len(arabic_letter) * 20
        text_height = 30

    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2 - size // 12

    # Draw main letter with gold color for elegance
    draw.text((text_x, text_y), arabic_letter, fill=GOLD, font=font)

    # Add "تفسير" text below if size permits
    if size >= 128:
        full_text = "تفسير"
        try:
            small_font_size = int(size * 0.08)
            small_font = ImageFont.load_default()
        except:
            small_font = ImageFont.load_default()

        # Calculate position
        try:
            bbox2 = draw.textbbox((0, 0), full_text, font=small_font)
            text2_width = bbox2[2] - bbox2[0]
        except:
            text2_width = len(full_text) * 8

        text2_x = (size - text2_width) // 2
        text2_y = center + size // 8

        draw.text((text2_x, text2_y), full_text, fill=TEAL, font=small_font)

    # Add subtle geometric pattern touches (Islamic star points)
    if size >= 144:
        # Draw 8 small dots in octagonal pattern
        for i in range(8):
            angle = (math.pi * 2 * i) / 8
            dot_distance = size * 0.35
            dot_x = center + int(math.cos(angle) * dot_distance)
            dot_y = center + int(math.sin(angle) * dot_distance)
            dot_size = max(2, size // 64)
            draw.ellipse([dot_x - dot_size, dot_y - dot_size,
                         dot_x + dot_size, dot_y + dot_size],
                        fill=GOLD)

    return img

def create_maskable_icon(size):
    """Create a maskable icon with proper safe area"""
    # Maskable icons need 20% padding for safe area
    img = Image.new('RGBA', (size, size), CREAM)
    draw = ImageDraw.Draw(img)

    # Fill background with gradient effect
    draw.rectangle([0, 0, size, size], fill=CREAM)

    # Create the icon in safe area (80% of total size)
    safe_area_size = int(size * 0.8)
    padding = int(size * 0.1)

    # Create a smaller version of the icon
    icon = create_islamic_icon(safe_area_size)

    # Paste it centered
    img.paste(icon, (padding, padding), icon)

    return img

def main():
    output_dir = "frontend/public/icons"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating Islamic-themed PWA icons in {output_dir}/")
    print("Using Tafsir Simplified brand colors...")

    # Generate standard PWA icons
    for size in SIZES:
        # Create both regular and maskable versions
        icon = create_islamic_icon(size)
        filename = f"icon-{size}x{size}.png"
        filepath = os.path.join(output_dir, filename)
        icon.save(filepath, "PNG", optimize=True)
        print(f"  ✓ Created {filename}")

        # Also save maskable version for Android
        if size >= 192:
            maskable = create_maskable_icon(size)
            maskable_filename = f"icon-maskable-{size}x{size}.png"
            maskable_path = os.path.join(output_dir, maskable_filename)
            maskable.save(maskable_path, "PNG", optimize=True)
            print(f"  ✓ Created {maskable_filename} (maskable)")

    # Generate additional icons
    for name, size in ADDITIONAL_SIZES.items():
        icon = create_islamic_icon(size)
        if name == 'favicon-32':
            filename = 'favicon-32x32.png'
        elif name == 'favicon-16':
            filename = 'favicon-16x16.png'
        else:
            filename = f"{name}.png"
        filepath = os.path.join(output_dir, filename)
        icon.save(filepath, "PNG", optimize=True)
        print(f"  ✓ Created {filename}")

    # Create favicon.ico
    icon_16 = create_islamic_icon(16)
    icon_32 = create_islamic_icon(32)
    favicon_path = os.path.join("frontend/public", "favicon.ico")
    icon_32.save(favicon_path, format='ICO', sizes=[(16, 16), (32, 32)])
    print(f"  ✓ Created favicon.ico")

    print("\n✅ Islamic-themed icons generated successfully!")
    print("\nDesign features:")
    print("  • Teal & Deep Blue gradient (Islamic tiles)")
    print("  • Gold accents (calligraphy)")
    print("  • Arabic letter ت (Tafsir)")
    print("  • Geometric pattern touches")
    print("  • Matches app's premium Islamic aesthetic")

if __name__ == "__main__":
    main()