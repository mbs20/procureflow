import os
from PIL import Image

def compile_hero_gif():
    frames_dir = os.path.join(os.path.dirname(__file__), "frames")
    output_path = os.path.join(os.path.dirname(__file__), "hero_demo.gif")
    
    frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith(".png")])
    if not frame_files:
        print(f"No frames found in {frames_dir}")
        return

    print(f"Found {len(frame_files)} frames. Processing...")
    images = []
    # Configure custom durations for each frame to give viewers time to read
    # frame_01: review workspace (1800ms)
    # frame_02: clicked evidence / highlight (2000ms)
    # frame_03: highlight details (1500ms)
    # frame_04: matrix view (1800ms)
    # frame_05: matrix normalized details (1500ms)
    # frame_06: scoring breakdown & sensitivity (2000ms)
    # frame_07: formula view (1800ms)
    durations = [1800, 2000, 1500, 1800, 1500, 2000, 1800]

    for i, file_name in enumerate(frame_files):
        img_path = os.path.join(frames_dir, file_name)
        img = Image.open(img_path)
        # Resize to crisp, lightweight width (960px)
        w, h = img.size
        new_w = 960
        new_h = int(h * (new_w / w))
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Quantize to adaptive palette with dithering for small file size and high fidelity
        img_quantized = img_resized.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        images.append(img_quantized)

    actual_durations = [durations[i] if i < len(durations) else 1500 for i in range(len(images))]

    # Save animated GIF
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        optimize=True,
        duration=actual_durations,
        loop=0
    )
    
    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"Hero demo GIF successfully compiled to {output_path} ({file_size_kb:.1f} KB)")

if __name__ == "__main__":
    compile_hero_gif()
