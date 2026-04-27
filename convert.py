from PIL import Image
try:
    Image.open('icon.png').save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("Successfully converted icon.png to icon.ico")
except Exception as e:
    print(f"Error: {e}")
