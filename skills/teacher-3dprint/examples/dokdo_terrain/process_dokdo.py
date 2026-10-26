#!/usr/bin/env python3
"""Build a watertight Dokdo + seabed STL from GEBCO bathymetry and Copernicus DEM."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio
import trimesh
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.warp import reproject


DOKDO_LON = 131.869
DOKDO_LAT = 37.240
TARGET_CRS = "EPSG:32652"  # WGS 84 / UTM zone 52N
NODATA = -999999.0


def target_grid(extent_m: float, grid_spacing_m: float) -> tuple[int, Affine]:
    center = Transformer.from_crs("EPSG:4326", TARGET_CRS, always_xy=True)
    cx, cy = center.transform(DOKDO_LON, DOKDO_LAT)
    n = max(3, int(np.ceil(extent_m / grid_spacing_m)) + 1)
    step = extent_m / (n - 1)
    transform = Affine(
        step, 0, cx - extent_m / 2 - step / 2,
        0, -step, cy + extent_m / 2 + step / 2,
    )
    return n, transform


def warp(path: Path, n: int, transform: Affine, method: Resampling) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as src:
        if not src.crs:
            raise ValueError(f"{path} has no CRS; refusing to guess its coordinates")
        out = np.full((n, n), NODATA, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=transform,
            dst_crs=TARGET_CRS,
            dst_nodata=NODATA,
            resampling=method,
        )
        meta = {
            "path": str(path.resolve()),
            "crs": src.crs.to_string(),
            "dimensions_rows_cols": [src.height, src.width],
            "resolution_native_units": list(src.res),
            "nodata": src.nodata,
            "min": float(np.min(src.read(1, masked=True))),
            "max": float(np.max(src.read(1, masked=True))),
            "band_tags": src.tags(1),
        }
    return out, meta


def make_mesh(
    elevation: np.ndarray,
    size_mm: float,
    extent_m: float,
    base_mm: float,
    vertical_exaggeration: float,
) -> trimesh.Trimesh:
    rows, cols = elevation.shape
    scale = size_mm / extent_m * vertical_exaggeration
    top_z = (elevation - float(elevation.min())) * scale + base_mm
    xx, yy = np.meshgrid(np.linspace(0, size_mm, cols), np.linspace(size_mm, 0, rows))
    top = np.column_stack((xx.ravel(), yy.ravel(), top_z.ravel()))
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
    trimesh.repair.fix_normals(mesh, multibody=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or not mesh.is_volume or mesh.volume <= 0:
        raise RuntimeError("Mesh is not a valid closed printable volume")
    return mesh


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gebco", default="data/dokdo_gebco_2026_subset.tif")
    parser.add_argument("--tid", default="data/dokdo_gebco_2026_tid_subset.tif")
    parser.add_argument("--land-dem", default="data/Copernicus_DSM_COG_10_N37_00_E131_00_DEM.tif")
    parser.add_argument("--land-dataset", default="Copernicus DEM GLO-30")
    parser.add_argument("--land-source-url", default="https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM")
    parser.add_argument("--land-native-resolution", default="1 arc-second / approximately 30 m")
    parser.add_argument("--land-product-type", default="DSM")
    parser.add_argument("--land-classification", default="land cells are samples with elevation > 0 m")
    parser.add_argument("--land-vertical-reference", default="Not explicitly identified in raster metadata; no datum transformation was applied")
    parser.add_argument("--output-stem", default="dokdo_gebco_copernicus_200mm")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--preview-dir", default="preview")
    parser.add_argument("--extent-m", type=float, default=6000)
    parser.add_argument("--size-mm", type=float, default=200)
    parser.add_argument("--base-mm", type=float, default=3)
    parser.add_argument("--grid-spacing-m", type=float, default=30)
    parser.add_argument("--vertical-exaggeration", type=float, default=1.0)
    parser.add_argument("--land-threshold-m", type=float, default=0.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    bathy_path = (root / args.gebco).resolve()
    land_path = (root / args.land_dem).resolve()
    tid_path = (root / args.tid).resolve()
    output_dir = (root / args.output_dir).resolve()
    preview_dir = (root / args.preview_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    n, dst_transform = target_grid(args.extent_m, args.grid_spacing_m)

    bathymetry, bathy_meta = warp(bathy_path, n, dst_transform, Resampling.bilinear)
    land, land_meta = warp(land_path, n, dst_transform, Resampling.cubic)
    tid, tid_meta = warp(tid_path, n, dst_transform, Resampling.nearest)
    for label, grid in (("GEBCO bathymetry", bathymetry), ("GEBCO TID", tid)):
        invalid = ~np.isfinite(grid) | (grid == NODATA)
        if invalid.any():
            raise ValueError(f"{label} has {int(invalid.sum())} missing points in the output footprint")

    # Use positive land-raster elevations for the island; GEBCO supplies non-land samples.
    # Interpolate the zero-elevation crossing for a less pixelated coastline.
    # The 30 m source DEM still limits the actual shoreline detail.
    land_mask = np.isfinite(land) & (land != NODATA) & (land > args.land_threshold_m)
    if not land_mask.any():
        raise ValueError("No positive land-raster samples were found in the requested footprint")
    composite = bathymetry.copy()
    composite[land_mask] = land[land_mask]
    if args.vertical_exaggeration <= 0:
        raise ValueError("--vertical-exaggeration must be greater than zero")
    mesh = make_mesh(
        composite,
        args.size_mm,
        args.extent_m,
        args.base_mm,
        args.vertical_exaggeration,
    )

    stl_path = output_dir / f"{args.output_stem}.stl"
    mesh.export(stl_path)
    preview_path = preview_dir / f"{args.output_stem}_preview.png"
    fig, ax = plt.subplots(figsize=(9, 7), constrained_layout=True)
    im = ax.imshow(composite, cmap="terrain", origin="upper", extent=(0, args.size_mm, 0, args.size_mm))
    ax.contour(np.linspace(0, args.size_mm, n), np.linspace(args.size_mm, 0, n), land_mask.astype(float),
               levels=[0.5], colors="white", linewidths=0.5)
    ax.set_title(f"Dokdo + surrounding seabed\n{args.land_dataset} on land, GEBCO_2026 bathymetry at sea")
    ax.set_xlabel("Model X (mm)")
    ax.set_ylabel("Model Y (mm)")
    fig.colorbar(im, ax=ax, label="Source elevation (m)")
    fig.savefig(preview_path, dpi=180)
    plt.close(fig)

    report = {
        "sources": {
            "bathymetry": {
                **bathy_meta,
                "dataset": "GEBCO_2026",
                "source_url": "https://www.gebco.net/data-products/gridded-bathymetry-data",
                "native_resolution": "15 arc-seconds",
                "vertical_reference": "GEBCO elevation grid; no datum transformation was applied in this project",
            },
            "gebco_type_identifier": {
                **tid_meta,
                "resampled_value_counts": {str(int(k)): int(v) for k, v in zip(*np.unique(tid.astype(np.uint8), return_counts=True))},
                "note": "Retained as provenance and quality context; the TID values do not alter elevations.",
            },
            "land_surface": {
                **land_meta,
                "dataset": args.land_dataset,
                "source_url": args.land_source_url,
                "native_resolution": args.land_native_resolution,
                "product_type": args.land_product_type,
                "vertical_reference": args.land_vertical_reference,
            },
            "gebco_subset_coordinate_check": {
                "latitude_range_north": [37.21458333333334, 37.264583333333334],
                "longitude_range_east": [131.83541666666667, 131.90208333333334],
                "note": "Subset was re-requested after detecting an earlier erroneous south-latitude index range; only this corrected north-latitude raster is used.",
            },
        },
        "processing": {
            "target_crs": TARGET_CRS,
            "center_lon_lat": [DOKDO_LON, DOKDO_LAT],
            "extent_m": args.extent_m,
            "grid_shape_rows_cols": [n, n],
            "grid_spacing_m": args.extent_m / (n - 1),
            "resampling": "bilinear for bathymetry, cubic interpolation for land elevations and zero-elevation shoreline; GEBCO for sea and positive samples from the selected land raster for land",
            "land_classification": args.land_classification,
            "land_threshold_m": args.land_threshold_m,
            "source_elevation_range_m": [float(composite.min()), float(composite.max())],
            "land_sample_count": int(land_mask.sum()),
            "land_sample_fraction": float(land_mask.mean()),
        },
        "model": {
            "stl_path": str(stl_path),
            "preview_path": str(preview_path),
            "footprint_mm": [args.size_mm, args.size_mm],
            "base_thickness_mm": args.base_mm,
            "vertical_exaggeration": args.vertical_exaggeration,
            "model_height_mm": float(mesh.bounds[1, 2]),
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "is_volume": bool(mesh.is_volume),
            "volume_mm3": float(mesh.volume),
            "bounds_mm": mesh.bounds.tolist(),
        },
    }
    report_path = output_dir / "stl_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["model"], indent=2, ensure_ascii=False))
    print(f"surface range m: {composite.min():.1f} .. {composite.max():.1f}; land grid cells: {land_mask.sum()} / {land_mask.size}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
