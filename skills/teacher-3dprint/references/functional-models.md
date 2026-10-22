# Functional and assembled print models

Use this reference when the requested print must fit, move, or work as an assembly (for example, a wheeled car, snap fit, hinge, gear, or classroom mechanism).

## Design from use, not appearance alone

- Establish the intended action: display, demonstrate, rotate, roll, hold, or bear a load. A resemblance to the object does not establish that it will perform that action.
- Define overall dimensions and each part's relationship before generating meshes. Keep coordinates and shared dimensions consistent across parts.
- For moving joints, include a deliberate clearance suited to the printer, material, layer direction, and expected motion. If those are unknown, choose a conservative editable starting fit and call it a prototype assumption.
- Include retaining features and assembly access. A wheel needs a compatible axle and a way to stay on it while turning; a body and chassis need an attachment method; supports must leave clearance for intended motion.
- Prefer geometry that can print without unsupported overhangs or trapped supports. Orient parts to protect thin features and critical fit surfaces.

## Deliverables and claims

- Export each separately printable part as its own STL. Include an assembled preview or a simple diagram only if it helps explain orientation or assembly.
- Keep the parametric source or generation script alongside the STLs when the design is likely to need tuning.
- Provide a concise parts list with key dimensions, fit assumptions, assembly steps, and a small-fit test recommendation for friction/press fits.
- A mesh check can establish geometric properties; it cannot prove material strength, successful printing, fit on a specific printer, or real-world performance. State which of those remain untested.

