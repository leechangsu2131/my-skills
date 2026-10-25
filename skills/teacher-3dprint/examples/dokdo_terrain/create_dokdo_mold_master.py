#!/usr/bin/env python3
"""Create a raised Dokdo relief master for casting a shallow silicone mold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from rasterio.enums import Resampling
from trimesh.repair import fix_normals

from process_dokdo import NODATA, target_grid, warp


def make_closed_board(surface_z: np.ndarray, size_mm: float) -> trimesh.Trimesh:
    rows, cols = surface_z.shape
    xx, yy = np.meshgrid(np.linspace(0, size_mm, cols), np.linspace(size_mm, 0, rows))
    top = np.column_stack((xx.ravel(), yy.ravel(), surface_z.ravel()))
    bottom = top.copy()
    bottom[:, 2] = 0.0
    vertices = np.vstack((top, bottom))
    offset = rows * cols
    faces: list[tuple[int, int, int]] = []

    for r in range(rows - 1):
        for c in range(cols - 1):
            nw = r * cols + c
            ne, sw, se = nw + 1, nw + cols, nw + cols + 1
            faces.extend(((sw, se, ne), (sw, ne, nw)))
            faces.extend(((offset + sw, offset + ne, offset + se),
                          (offset + sw, offset + nw, offset + ne)))

    def wall(a: int, b: int) -> None:
        faces.extend(((a, offset + b, b), (a, offset + a, offset + b)))

    for c in range(cols - 1):
        wall(c, c + 1)
        south = (rows - 1) * cols + c
        wall(south + 1, south)
    for r in range(rows - 1):
        west = r * cols
        wall(west, west + cols)
        east = r * cols + cols - 1
        wall(east + cols, east)

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)
    fix_normals(mesh, multibody=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or not mesh.is_volume or mesh.volume <= 0:
        raise RuntimeError("Master mesh is not a valid closed volume")
    return mesh


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--land-dem", default="data/Copernicus_DSM_COG_10_N37_00_E131_00_DEM.tif")
    parser.add_argument("--land-dataset", default="Copernicus DEM GLO-30")
    parser.add_argument("--extent-m", type=float, default=900)
    parser.add_argument("--center-offset-x-m", type=float, default=-175)
    parser.add_argument("--center-offset-y-m", type=float, default=112)
    parser.add_argument("--size-mm", type=float, default=80)
    parser.add_argument("--grid-spacing-m", type=float, default=3)
    parser.add_argument("--base-mm", type=float, default=3)
    parser.add_argument("--vertical-exaggeration", type=float, default=2)
    parser.add_argument("--land-threshold-m", type=float, default=1)
    parser.add_argument("--output-dir", default="output/mold_master")
    parser.add_argument("--preview-dir", default="preview/mold_master")
    parser.add_argument("--output-stem", default="dokdo_relief_mandu_master_80mm")
    args = parser.parse_args()

    if args.extent_m <= 0 or args.size_mm <= 0 or args.grid_spacing_m <= 0:
        raise ValueError("extent, model size, and grid spacing must be positive")
    if args.base_mm <= 0 or args.vertical_exaggeration <= 0:
        raise ValueError("base thickness and vertical exaggeration must be positive")

    root = Path(__file__).resolve().parent
    source = (root / args.land_dem).resolve()
    output_dir = (root / args.output_dir).resolve()
    preview_dir = (root / args.preview_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    n, transform = target_grid(args.extent_m, args.grid_spacing_m)
    transform = type(transform)(
        transform.a, transform.b, transform.c + args.center_offset_x_m,
        transform.d, transform.e, transform.f + args.center_offset_y_m,
    )
    elevation, source_meta = warp(source, n, transform, Resampling.cubic)
    valid = np.isfinite(elevation) & (elevation != NODATA)
    land_mask = valid & (elevation > args.land_threshold_m)
    if not land_mask.any():
        raise ValueError("No land cells were found above the requested threshold")

    # The board is level; only positive island relief rises above it.
    mm_per_m = args.size_mm / args.extent_m * args.vertical_exaggeration
    relief_mm = np.where(land_mask, (elevation - args.land_threshold_m) * mm_per_m, 0.0)
    surface_z = args.base_mm + np.maximum(relief_mm, 0.0)
    mesh = make_closed_board(surface_z, args.size_mm)

    stl_path = output_dir / f"{args.output_stem}.stl"
    mesh.export(stl_path)
    preview_path = preview_dir / f"{args.output_stem}_preview.png"
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    ax.imshow(surface_z - args.base_mm, cmap="terrain", origin="upper", extent=(0, args.size_mm, 0, args.size_mm))
    ax.contour(np.linspace(0, args.size_mm, n), np.linspace(args.size_mm, 0, n), land_mask.astype(float),
               levels=[0.5], colors="black", linewidths=0.5)
    ax.set_title("Dokdo relief master for silicone casting")
    ax.set_xlabel("Master X (mm)")
    ax.set_ylabel("Master Y (mm)")
    fig.savefig(preview_path, dpi=180)
    plt.close(fig)

    report = {
        "purpose": "Positive printed master for casting a shallow negative silicone relief mold; the master is not for food contact.",
        "source": {
            **source_meta,
            "dataset": args.land_dataset,
            "native_resolution": "1 arc-second / approximately 30 m",
            "source_url": "https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM",
        },
        "processing": {
            "target_crs": "EPSG:32652",
            "extent_m": args.extent_m,
            "center_offset_from_dokdo_center_m": [args.center_offset_x_m, args.center_offset_y_m],
            "grid_shape_rows_cols": [n, n],
            "grid_spacing_m": args.extent_m / (n - 1),
            "resampling": "cubic for elevation and interpolated shoreline",
            "land_threshold_m": args.land_threshold_m,
            "land_sample_count": int(land_mask.sum()),
            "elevation_range_land_m": [float(elevation[land_mask].min()), float(elevation[land_mask].max())],
            "vertical_exaggeration": args.vertical_exaggeration,
        },
        "model": {
            "stl_path": str(stl_path),
            "preview_path": str(preview_path),
            "footprint_mm": [args.size_mm, args.size_mm],
            "base_thickness_mm": args.base_mm,
            "relief_height_mm": float(relief_mm.max()),
            "bounds_mm": mesh.bounds.tolist(),
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "is_volume": bool(mesh.is_volume),
        },
    }
    report_path = output_dir / "stl_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["model"], indent=2, ensure_ascii=False))
    print(f"land cells: {land_mask.sum()} / {land_mask.size}; relief max: {relief_mm.max():.2f} mm")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
