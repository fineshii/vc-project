import numpy as np
from PIL import Image
import os
import random

def binarize(image_path):
    """Convert image to binary (black and white)"""
    img = Image.open(image_path).convert('L')
    binary = (np.array(img) < 128).astype(np.uint8)
    return binary

def generate_kn_shares(binary, k, n, output_folder="assets/shares"):
    """Generate n shares for a (k,n) threshold VC scheme using pixel expansion"""
    os.makedirs(output_folder, exist_ok=True)
    h, w = binary.shape
    m = n  # pixel expansion factor

    shares = [np.zeros((h * m, w * m), dtype=np.uint8) for _ in range(n)]

    # Basis matrices for black and white pixels
    def generate_basis(pixel_type):
        base = np.zeros((n, m), dtype=np.uint8)
        if pixel_type == "white":
            # All rows identical for white pixel
            pattern = np.random.permutation([1] * (m // 2) + [0] * (m - m // 2))
            for i in range(n):
                base[i] = pattern
        else:
            # Rows differ for black pixel
            for i in range(n):
                base[i] = np.random.permutation([1] * (m // 2) + [0] * (m - m // 2))
        return base

    for i in range(h):
        for j in range(w):
            pixel = binary[i, j]
            basis = generate_basis("black" if pixel == 1 else "white")
            for s in range(n):
                block = basis[s].reshape((m, 1)).repeat(m, axis=1)
                shares[s][i*m:(i+1)*m, j*m:(j+1)*m] = block

    for idx, share in enumerate(shares):
        Image.fromarray(share * 255).save(f"{output_folder}/share_{idx+1}.png")

def overlay_kn_shares(share_paths, output_path="reconstructed_kn.png"):
    """Overlay k or more shares to reconstruct the image"""
    combined = None
    for path in share_paths:
        img = Image.open(path).convert('L')
        binary = (np.array(img) < 128).astype(np.uint8)
        if combined is None:
            combined = binary
        else:
            combined = np.bitwise_or(combined, binary)

    Image.fromarray(combined * 255).save(output_path)
    Image.fromarray(combined * 255).show()


def progressive_reveal(share_paths, output_folder="static/reveal"):
        """
        Progressively overlays shares to show how the image clarity improves.
        Assumes binary shares (0 = white, 1 = black).
        """
        os.makedirs("static/reveal", exist_ok=True)

    # Load first share as base
        base = np.array(Image.open(share_paths[0]).convert('L')) < 128
        current = base.astype(np.uint8)

        for i, path in enumerate(share_paths[1:], start=1):
         share = np.array(Image.open(path).convert('L')) < 128
         current = np.bitwise_or(current, share.astype(np.uint8))
         Image.fromarray(current * 255).save(f"{"static/reveal"}/step_{i}.png")