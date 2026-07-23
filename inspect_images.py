from PIL import Image
import os

brain_dir = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\3201d54d-43ea-4579-a1e2-b087654169d0"
for f in os.listdir(brain_dir):
    if f.endswith(('.png', '.jpg', '.jpeg')):
        p = os.path.join(brain_dir, f)
        img = Image.open(p)
        print(f"File: {f}, Format: {img.format}, Size: {img.size}, Mode: {img.mode}")
