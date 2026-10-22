#!/usr/bin/env python3
"""Convert a small GEBCO OPeNDAP ASCII subset to a georeferenced GeoTIFF."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "dokdo_gebco_2026_subset.txt"
DEST = ROOT / "data" / "dokdo_gebco_2026_subset.tif"
TID_SOURCE = ROOT / "data" / "dokdo_gebco_2026_tid_subset.txt"
TID_DEST = ROOT / "data" / "dokdo_gebco_2026_tid_subset.tif"
STEP = 1.0 / 240.0  # GEBCO 15-arc-second grid


def vector(text: str, name: str, size: int) -> np.ndarray:
    match = re.search(rf"(?m)^{re.escape(name)}\[{size}\]\s*\n([^\r\n]+)", text)
    if not match:
        raise ValueError(f"Missing {name}[{size}] coordinate vector")
    values = np.fromstring(match.group(1), sep=",")
    if len(values) != size:
        raise ValueError(f"Expected {size} {name} values, got {len(values)}")
    return values


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    shape = re.search(r"elevation\[lat = (\d+)\]\[lon = (\d+)\]", text)
    if not shape:
        raise ValueError("ASCII response has no elevation grid shape")
    rows, cols = map(int, shape.groups())
    lons = vector(text, "lon", cols)
    lats = vector(text, "lat", rows)
    grid_match = re.search(
        rf"(?ms)^elevation\.elevation\[{rows}\]\[{cols}\]\s*\n(.*?)(?=^\s*$)", text
    )
    if not grid_match:
        raise ValueError("ASCII response has no elevation matrix")
    grid_lines = [line.strip() for line in grid_match.group(1).splitlines() if line.strip()]
    values = []
    for expected_idx, line in enumerate(grid_lines):
        idx_text, row_text = line.split("]", 1)
        if int(idx_text.lstrip("[")) != expected_idx:
            raise ValueError("Elevation matrix row indices are not contiguous")
        row = np.fromstring(row_text.lstrip(", "), sep=",")
        if len(row) != cols:
            raise ValueError(f"Expected {cols} values in row {expected_idx}, got {len(row)}")
        values.append(row)
    elevation = np.asarray(values, dtype=np.float32)
    if elevation.shape != (rows, cols):
        raise ValueError(f"Expected grid {(rows, cols)}, got {elevation.shape}")
    if not (lats.min() > 0 and lats.min() < 37.240 < lats.max()):
        raise ValueError(f"Latitude axis does not contain Dokdo at 37.240N: {lats.min()}..{lats.max()}")
    if not (lons.min() < 131.869 < lons.max()):
        raise ValueError("Longitude axis does not contain Dokdo at 131.869E")
    if len(lons) > 1 and not np.allclose(np.diff(lons), STEP, atol=1e-10):
        raise ValueError("Unexpected longitude spacing")
    if len(lats) > 1 and not np.allclose(np.diff(lats), STEP, atol=1e-10):
        raise ValueError("Unexpected latitude spacing or orientation")

    transform = from_origin(lons.min() - STEP / 2, lats.max() + STEP / 2, STEP, STEP)
    profile = {
        "driver": "GTiff",
        "height": rows,
        "width": cols,
        "count": 1,
        "dtype": "int16",
        "crs": "EPSG:4326",
        "transform": transform,
        "compress": "deflate",
    }
    with rasterio.open(DEST, "w", **profile) as dst:
        dst.write(elevation.astype(np.int16), 1)
        dst.update_tags(
            source="GEBCO_2026 OPeNDAP ASCII subset",
            variable="elevation",
            source_grid_spacing="15 arc-seconds",
            latitude_range_north="true",
            datum="GEBCO nominal sea-level referenced elevation; see source metadata",
        )
    tid_text = TID_SOURCE.read_text(encoding="utf-8")
    tid_shape = re.search(r"tid\[lat = (\d+)\]\[lon = (\d+)\]", tid_text)
    if not tid_shape or tuple(map(int, tid_shape.groups())) != (rows, cols):
        raise ValueError("The matching GEBCO TID grid is missing or has different dimensions")
    tid_match = re.search(
        rf"(?ms)^tid\.tid\[{rows}\]\[{cols}\]\s*\n(.*?)(?=^\s*$)", tid_text
    )
    if not tid_match:
        raise ValueError("TID ASCII response has no identifier matrix")
    tid_lines = [line.strip() for line in tid_match.group(1).splitlines() if line.strip()]
    tid_values = []
    for expected_idx, line in enumerate(tid_lines):
        idx_text, row_text = line.split("]", 1)
        if int(idx_text.lstrip("[")) != expected_idx:
            raise ValueError("TID matrix row indices are not contiguous")
        row = np.fromstring(row_text.lstrip(", "), sep=",")
        if len(row) != cols:
            raise ValueError(f"Expected {cols} identifiers in TID row {expected_idx}, got {len(row)}")
        tid_values.append(row)
    tid_grid = np.asarray(tid_values, dtype=np.uint8)
    if tid_grid.shape != (rows, cols):
        raise ValueError(f"Expected TID grid {(rows, cols)}, got {tid_grid.shape}")
    tid_profile = {**profile, "dtype": "uint8"}
    with rasterio.open(TID_DEST, "w", **tid_profile) as dst:
        dst.write(tid_grid, 1)
        dst.update_tags(source="GEBCO_2026 Type Identifier grid", paired_with=DEST.name)
    print(f"saved={DEST}")
    print(f"saved_tid={TID_DEST}; tid_codes={dict(zip(*np.unique(tid_grid, return_counts=True)))}")
    print(f"shape={elevation.shape}; lon={lons.min():.8f}..{lons.max():.8f}; lat={lats.min():.8f}..{lats.max():.8f}")
    print(f"elevation_m={elevation.min():.0f}..{elevation.max():.0f}; dokdo_center_near={elevation[np.argmin(abs(lats-37.24)), np.argmin(abs(lons-131.869))]:.0f}")


if __name__ == "__main__":
    main()
