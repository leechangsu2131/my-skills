---
name: teacher-3dprint
description: Design classroom-friendly 3D-printable models and deliver usable STL files, including data-based terrain models when real elevation data is required.
---

# Teacher 3D Print

Help a teacher turn a lesson idea, object, or real-world feature into a practical 3D-printing deliverable. When the user asks for an STL, the expected result is an actual STL file saved to the workspace, not only modeling advice or code in chat.

## Choose the modeling path

- **Designed object or teaching aid:** Translate the requested use into dimensions, printable parts, and assembly details. Read [references/functional-models.md](references/functional-models.md) when the model has moving, mating, load-bearing, or multi-part features.
- **Food mold or stamp:** Design a positive master for silicone casting when food will touch the finished silicone mold. Read [references/food-mold-masters.md](references/food-mold-masters.md); do not describe an ordinary FDM print as food-safe.
- **Real terrain or other measured subject:** Use verified source data and preserve its provenance. Read [references/terrain-stl-workflow.md](references/terrain-stl-workflow.md) before acquiring, combining, or meshing geospatial data.
- **Illustrative or invented shape:** A generated shape is acceptable when the user asks for a concept or stylized model. Label it as illustrative; do not present it as a faithful measured object.

When the user supplies or prefers an existing downloadable model, inspect its source, license, dimensions, and mesh integrity before recommending it. Preserve attribution and license terms with any copy saved in the skill folder; check that the slicer preview can repair or print the mesh.

The completed Dokdo terrain example, including its STL, source rasters, preview, and regeneration scripts, is in [examples/dokdo_terrain/README.md](examples/dokdo_terrain/README.md).

## Work toward a printable deliverable

1. Identify the intended learning/use, approximate final size, printer or material constraints, and whether the model should be one piece or assembled. Infer ordinary choices where practical; ask only when an unresolved choice would materially change the model.
2. When the task requires using a website, read the installed `aside-browser` skill and follow its workflow. Run `aside guide` before Aside work; use the Aside CLI (usually `aside exec`) for website tasks, and use `aside repl` only when direct DOM or screenshot inspection is needed (after `aside guide repl`). Use local tools for file processing and mesh generation.
3. Choose a modeling method that suits the geometry and available tools, such as OpenSCAD, Blender, CAD, or a purpose-built mesh script. Keep reusable source files with the output when they help the user revise or regenerate it.
4. Build the actual geometry. For assemblies, design the interfaces together: fit, clearance, retention, motion, orientation, and print orientation must agree across parts.
5. Export STL file(s) in millimeters where the tool supports units. Save them in a clearly named output folder, with a short Korean README describing parts, dimensions, orientation, assembly, and known limits when the set is not self-explanatory.
6. Inspect the exported mesh and its bounding dimensions. Check for degenerate faces, open boundaries, inconsistent normals, unintended intersections, and watertightness where a closed solid is required. Reopen the exported STL in a mesh or slicer tool if one is available; do not claim checks that were not performed.
7. Report the exact output paths, dimensions, what was verified, and any remaining fit or print assumptions. Distinguish a visual/concept model from a tested functional prototype.

## Boundaries

- Do not stop at a recipe or a code snippet when an STL deliverable was requested and the workspace can produce it.
- Do not imply that separate parts assemble or move correctly just because they were exported. Design and inspect their mating geometry; state any untested tolerances.
- For data-driven models, do not invent, silently interpolate, or mislabel source measurements. If data is unavailable or incompatible, report the limitation and offer a clearly labeled alternative.
- Use public and user-provided materials within their stated terms. Do not bypass access controls or proceed through payment, personal-data submission, or binding terms acceptance on the user's behalf.

