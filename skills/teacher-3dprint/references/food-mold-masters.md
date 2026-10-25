# Food mold masters

Use this reference when a printed part will be used as a positive pattern to cast a silicone mold for food.

## Model for release and casting

- Confirm whether the user wants a shallow face relief, an outline-shaped cavity, or a multi-part mold. For a simple bun or chocolate imprint, a shallow relief master is usually easiest to demold.
- Save the printed master as a separate artifact and identify it as a pattern for making a mold, not as the food-contact mold itself.
- Prefer continuous, watertight geometry with gently sloped relief and no trapped undercuts. Keep thin details large enough to survive printing and silicone casting.
- Include a flat backing face or casting flange where useful. State the finished master dimensions, relief depth, orientation, and any features simplified from the source.
- Inspect the STL and, when available, the slicer preview. A valid STL does not establish food-contact suitability.

## Food-contact material notes

- Do not infer that a silicone is food-contact suitable from the words “platinum cure,” “food grade,” or a general claim such as “FDA compliant” alone. The finished material, ingredients, intended food, temperature, repeated-use conditions, and cure instructions matter.
- Ask the silicone manufacturer for documentation covering the exact product and intended use. Follow its mix ratio, cure schedule, post-cure, cleaning, and temperature limits.
- Do not make blanket claims that every tin-cure silicone is prohibited or that every platinum-cure silicone is suitable; verify the specific formulation and authorization.
- In the United States, [21 CFR 177.2600](https://www.ecfr.gov/current/title-21/section-177.2600) addresses rubber articles intended for repeated food use and has conditions for particular food types. See also FDA guidance on [determining regulatory status of food-contact components](https://www.fda.gov/food/packaging-food-contact-substances-fcs/determining-regulatory-status-components-food-contact-material).

## Dokdo example

`examples/dokdo_terrain/create_dokdo_mold_master.py` builds a shallow positive relief master from the Copernicus DEM. It is an illustrative terrain imprint, not a food-contact surface and not a substitute for a high-resolution shoreline survey.
