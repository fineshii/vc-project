from flask import Flask, render_template, request, send_file, redirect, flash
from vc_threshold_kn import binarize, generate_kn_shares, overlay_kn_shares, progressive_reveal
from PIL import Image
import os
import shutil

app = Flask(__name__)
app.secret_key = "vc_secret_key"

# canonical folders (use Flask static folder for web-served assets)
UPLOAD_FOLDER = "assets"
SHARE_FOLDER = os.path.join(app.static_folder, "shares")
REVEAL_FOLDER = os.path.join(app.static_folder, "reveal")
OUTPUT_FOLDER = os.path.join(app.static_folder, "output")

def clean_folder(folder):
    os.makedirs(folder, exist_ok=True)
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        try:
            os.remove(path)
        except PermissionError:
            print(f"Skipping locked file: {path}")

def migrate_assets_reveal():
    """Move any existing assets/reveal files into static/reveal (one-time migration)."""
    src = os.path.join(UPLOAD_FOLDER, "reveal")
    dst = REVEAL_FOLDER
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            try:
                shutil.move(os.path.join(src, f), os.path.join(dst, f))
            except Exception as e:
                print("Failed to migrate", f, e)
        # Optionally remove the empty folder
        try:
            os.rmdir(src)
        except OSError:
            pass

def count_reveal_steps():
    """Return the maximum step index found in static/reveal (0 if none)."""
    max_idx = 0
    if os.path.isdir(REVEAL_FOLDER):
        for name in os.listdir(REVEAL_FOLDER):
            if name.startswith("step_") and name.endswith(".png"):
                try:
                    idx = int(name[len("step_"):-4])
                    max_idx = max(max_idx, idx)
                except ValueError:
                    pass
    return max_idx

@app.route("/", methods=["GET", "POST"])
def index():
    shares = []
    k = n = 0

    # Ensure static folders exist and migrate stray reveal files if any
    os.makedirs(SHARE_FOLDER, exist_ok=True)
    os.makedirs(REVEAL_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    migrate_assets_reveal()

    if request.method == "POST":
        if "generate" in request.form:
            k = int(request.form["k"])
            n = int(request.form["n"])
            resize = int(request.form.get("resize", 100))
            image = request.files["image"]

            # Save uploaded image (avoid reopening the same file)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            image_path = os.path.join(UPLOAD_FOLDER, "input.png")
            with Image.open(image) as img:
                img = img.convert('L').resize((resize, resize))
                img.save(image_path)

            # Clean shares/reveal/output (we kept the uploaded input)
            clean_folder(SHARE_FOLDER)
            clean_folder(REVEAL_FOLDER)
            clean_folder(OUTPUT_FOLDER)

            # Generate shares (writes into SHARE_FOLDER)
            binary = binarize(image_path)
            generate_kn_shares(binary, k, n, output_folder=SHARE_FOLDER)
            shares = [f"{SHARE_FOLDER}/share_{i+1}.png" for i in range(n)]

            # Count how many reveal steps exist (likely 0 until reconstruction)
            reveal_steps = count_reveal_steps()
            return render_template("index.html", shares=shares, k=k, n=n, reveal_steps=reveal_steps)

        elif "reconstruct" in request.form:
            selected_ids = request.form.getlist("selected_shares")
            k = int(request.form["k"]) if "k" in request.form else len(selected_ids)
            n = int(request.form["n"])
            selected_paths = [os.path.join(SHARE_FOLDER, f"share_{i}.png") for i in map(int, selected_ids)]

            print("Selected shares:", selected_ids)
            print("Using k =", k, "with", len(selected_paths), "shares")

            if len(selected_paths) >= k:
                # overlay into OUTPUT_FOLDER and generate reveal steps into REVEAL_FOLDER
                os.makedirs(OUTPUT_FOLDER, exist_ok=True)
                os.makedirs(REVEAL_FOLDER, exist_ok=True)

                overlay_kn_shares(selected_paths, output_path=os.path.join(OUTPUT_FOLDER, "reconstructed.png"))
                # Important: pass the canonical REVEAL_FOLDER so images are written to static/reveal
                progressive_reveal(selected_paths, output_folder=REVEAL_FOLDER)
            else:
                flash(f"Select at least {k} shares to reconstruct the image.")
                return redirect("/")

            shares = [f"{SHARE_FOLDER}/share_{i}.png" for i in range(1, n+1)]
            reveal_steps = count_reveal_steps()
            return render_template("index.html", shares=shares, k=k, n=n, reveal_steps=reveal_steps)

    # GET request
    reveal_steps = count_reveal_steps()
    return render_template("index.html", shares=shares, k=k, n=n, reveal_steps=reveal_steps)

@app.route("/download/<path:filename>")
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)