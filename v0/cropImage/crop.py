#!/usr/bin/env python3
"""
Crop a sprite sheet into grid cells and name them by fixed row order:
row 0 -> down
row 1 -> left
row 2 -> right
row 3 -> up

Outputs:
  /mnt/data/ash_crops_fixed_order/ash_down_0.png, ash_down_1.png, ...
  /mnt/data/ash_crops_fixed_order/mapping.txt
"""
import os
from collections import Counter
from PIL import Image
import numpy as np

IN_PATH = "ash_main_img.png"
OUT_DIR = "ash_crops_output"

os.makedirs(OUT_DIR, exist_ok=True)

DIR_ORDER = ["down", "left", "right", "up"]  # fixed mapping for rows

def load_image(path):
    return Image.open(path).convert("RGBA")

def guess_bg_color(im):
    w, h = im.size
    corners = [im.getpixel((0,0)), im.getpixel((w-1,0)), im.getpixel((0,h-1)), im.getpixel((w-1,h-1))]
    if any(c[3] < 255 for c in corners):
        return None
    rgb = [(c[0], c[1], c[2]) for c in corners]
    return Counter(rgb).most_common(1)[0][0]

def make_mask(im, bg_color):
    arr = np.array(im)  # H x W x 4
    if bg_color is None:
        mask = arr[...,3] > 0
    else:
        bg = np.array(bg_color, dtype=np.uint8)
        mask = np.any(arr[...,:3] != bg.reshape((1,1,3)), axis=2)
    return mask.astype(np.uint8)

def find_segments_1d(bool_arr, min_len=1):
    segs = []
    inside = False
    start = 0
    for i, v in enumerate(bool_arr):
        if v and not inside:
            inside = True
            start = i
        elif not v and inside:
            inside = False
            end = i-1
            if end - start + 1 >= min_len:
                segs.append((start, end))
    if inside:
        end = len(bool_arr)-1
        if end - start + 1 >= min_len:
            segs.append((start, end))
    return segs

def crop_grid_cells(im, mask):
    # mask: HxW of 0/1
    row_presence = mask.sum(axis=1) > 0
    col_presence = mask.sum(axis=0) > 0
    row_segs = find_segments_1d(row_presence)
    col_segs = find_segments_1d(col_presence)

    if not row_segs or not col_segs:
        raise RuntimeError("Failed to detect row/column segments. Check the image/background.")

    cells = []  # list of dicts {row_idx, col_idx, image, bbox_sheet}
    for r_idx, (r0, r1) in enumerate(row_segs):
        for c_idx, (c0, c1) in enumerate(col_segs):
            # crop sheet region
            crop = im.crop((c0, r0, c1+1, r1+1))
            # tighten crop to non-background inside the cell
            ca = np.array(crop)
            alpha = ca[...,3]
            if alpha.max() == 0:
                non_bg = np.any(ca[...,:3] != 0, axis=2)
            else:
                non_bg = alpha > 0
            ys = np.where(non_bg.any(axis=1))[0]
            xs = np.where(non_bg.any(axis=0))[0]
            if ys.size and xs.size:
                ty0, ty1 = ys[0], ys[-1]
                tx0, tx1 = xs[0], xs[-1]
                tight = crop.crop((int(tx0), int(ty0), int(tx1)+1, int(ty1)+1))
            else:
                tight = crop
            cells.append({
                "row_index": r_idx,
                "col_index": c_idx,
                "bbox_sheet": (c0, r0, c1+1, r1+1),
                "image": tight
            })
    # sort row-major
    cells.sort(key=lambda x: (x["row_index"], x["col_index"]))
    return cells, row_segs, col_segs

def save_cells_fixed_order(cells, row_count):
    # Organize by row index
    rows = {}
    for c in cells:
        rows.setdefault(c["row_index"], []).append(c)
    # sort columns within rows by col_index
    for r in rows:
        rows[r].sort(key=lambda x: x["col_index"])

    mapping_lines = []
    for r_idx in sorted(rows.keys()):
        dir_name = DIR_ORDER[r_idx] if r_idx < len(DIR_ORDER) else f"row{r_idx}"
        for i, cell in enumerate(rows[r_idx]):
            fname = f"ash_{dir_name}_{i}.png"
            outp = os.path.join(OUT_DIR, fname)
            cell["image"].save(outp)
            mapping_lines.append(f"{fname} <- row {r_idx} col {cell['col_index']} bbox {cell['bbox_sheet']}")
    # write mapping
    with open(os.path.join(OUT_DIR, "mapping.txt"), "w") as f:
        f.write("\n".join(mapping_lines))
    print(f"Saved {len(cells)} images into {OUT_DIR}")
    print("Mapping written to mapping.txt")

def main():
    im = load_image(IN_PATH)
    bg = guess_bg_color(im)
    print("Background:", "transparent" if bg is None else bg)
    mask = make_mask(im, bg)
    cells, rows, cols = crop_grid_cells(im, mask)
    print(f"Detected grid: {len(rows)} rows x {len(cols)} cols -> {len(cells)} cells")
    save_cells_fixed_order(cells, len(rows))

if __name__ == "__main__":
    main()
