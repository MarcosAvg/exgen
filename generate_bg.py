from PIL import Image, ImageDraw

def create_placeholder_bg():
    width, height = 1275, 1650  # Letter size at ~150 DPI
    image = Image.new("RGB", (width, height), (245, 245, 250))
    draw = ImageDraw.Draw(image)
    
    # Draw some placeholder pattern or border
    draw.rectangle([50, 50, width-50, height-50], outline=(200, 200, 215), width=10)
    
    # Save the background image
    image.save("assets/background.jpg", "JPEG", quality=90)
    print("Placeholder background image created at assets/background.jpg")

if __name__ == "__main__":
    create_placeholder_bg()
