from vc_threshold_kn import binarize, generate_kn_shares, overlay_kn_shares

image_path = "assets/input.png"
binary = binarize(image_path)

n = 5  # total shares
k = 3  # threshold

generate_kn_shares(binary, k, n)

# Pick any k shares to reconstruct
selected = [
    "assets/shares/share_2.png",
    "assets/shares/share_3.png",
    "assets/shares/share_4.png",
    "assets/shares/share_5.png"
]

overlay_kn_shares(selected)