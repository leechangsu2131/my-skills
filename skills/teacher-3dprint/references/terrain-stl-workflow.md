# Measured terrain to STL

Use this reference when the user wants a geographically faithful terrain model, such as an island with surrounding seabed. Keep data discovery, data validation, and mesh generation distinct so an attractive model does not conceal missing or weak source data.

## 1. Establish the specification

Record the requested area, final footprint, vertical exaggeration (or a true-scale preference), base thickness, and whether land only or land plus bathymetry is in scope. If the user has not fixed a value, select a sensible provisional value and label it; ask only when the choice changes the intended lesson or scale materially.

## 2. Acquire and document source data

- Prefer actual elevation/bathymetry grids from authoritative providers or files supplied by the user. For any website discovery or download, read the installed `aside-browser` skill, run `aside guide`, and follow its current guide. Use `aside exec` for ordinary browsing and `aside repl` only when direct DOM or screenshot inspection is needed (read `aside guide repl` first). Use local tools for file inspection and processing; browser automation does not create or validate an STL.
- Distinguish a downloadable raster/grid from a map image, rendered contour map, paper figure, or service preview. Do not report a source file as acquired unless it exists locally and has been inspected.
- Record direct source URL, provider, dataset/version, download date, license or use terms, file path, coordinate reference system, horizontal resolution, units, vertical datum, elevation range, and nodata representation where available.
- For bathymetry with a source-identification or Type Identifier grid, inspect it when available. Explain where values are measured, estimated, or interpolated if the provider documents that distinction.
- When a download service takes grid row/column indices, inspect the returned coordinate arrays and verify they fall inside the requested longitude/latitude box before accepting or processing the subset. Never infer the hemisphere from the row number alone.
- If a login, fee, personal information, or binding terms acceptance is required, stop at that gate and explain the available next step. Do not treat a prior request to make the model as permission for those actions.

## 3. Validate before combining

Inspect raster metadata and a cropped preview. Confirm the area covers the requested footprint, values and nodata are plausible, and the horizontal and vertical reference systems are understood. Reproject to an appropriate metric coordinate system before setting physical scale. Align land and seafloor grids only when their units and vertical datums can be reconciled. If the datum is unavailable, do not silently apply an offset; describe the coastal seam and elevation limitation, and get the user's choice when datum accuracy is central to the request. Do not fill unknown coastal gaps with zero or smooth them away without an explicit, documented method.

If source resolution is coarse relative to the final model, state the approximate grid spacing on the print and what features it cannot resolve. Resampling can make a mesh denser but cannot add measured detail. If only partial or incompatible inputs are available, report that and ask whether to proceed with a clearly labeled partial/illustrative model when that changes the user's stated fidelity goal.

For a small island or other compact subject, check both the geographic crop and the physical print size before meshing. Estimate how large one native raster cell will be on the print (`native cell size × print width ÷ real-world crop width`). If the resulting edge step is too visible, obtain a finer elevation grid or a suitable shoreline vector; denser mesh sampling alone will not improve it. Use a positive-elevation threshold only to address documented near-shore noise, and record the threshold because it changes the modeled coastline.

## 4. Build and verify the solid

- Crop to the chosen extent, document its real-world bounds, and scale the horizontal footprint to the requested millimeters. Apply vertical exaggeration only as specified or clearly disclosed.
- Convert the surface grid into a triangulated surface, join its perimeter to vertical walls and a bottom plane, and export a closed printable solid. Avoid bridging nodata or land/sea seams with fabricated values.
- Check the exported STL's bounding dimensions, triangle validity, closed boundaries/watertightness, normals, and base thickness. Reopen it in a slicer when available and inspect the slice preview for missing islands, holes, or disconnected fragments.
- Save the STL, the processing script or reproducible steps, source metadata, and a concise report together. Label previews and output with the data version and scale where useful.

## 5. Report honestly

Summarize source files actually used, coverage, CRS/datum, native resolution, output footprint and vertical scale, processing choices, validation performed, and limitations. Keep a failed download separate from a successful acquisition, and do not call the result a measured/final model until the relevant files and exported mesh have been inspected.

