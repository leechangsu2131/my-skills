---
name: Waypoint Analysis System
colors:
  surface: '#fff9e9'
  surface-dim: '#e0dac7'
  surface-bright: '#fff9e9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#faf3df'
  surface-container: '#f4eeda'
  surface-container-high: '#eee8d4'
  surface-container-highest: '#e8e2cf'
  on-surface: '#1e1c10'
  on-surface-variant: '#4b4732'
  inverse-surface: '#333123'
  inverse-on-surface: '#f7f1dd'
  outline: '#7c775f'
  outline-variant: '#cdc7aa'
  surface-tint: '#6a5f00'
  primary: '#6a5f00'
  on-primary: '#ffffff'
  primary-container: '#fee500'
  on-primary-container: '#716600'
  inverse-primary: '#dec800'
  secondary: '#4c56af'
  on-secondary: '#ffffff'
  secondary-container: '#959efd'
  on-secondary-container: '#27308a'
  tertiary: '#5d5f5f'
  on-tertiary: '#ffffff'
  tertiary-container: '#e3e3e3'
  on-tertiary-container: '#636565'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#fde400'
  primary-fixed-dim: '#dec800'
  on-primary-fixed: '#201c00'
  on-primary-fixed-variant: '#504700'
  secondary-fixed: '#e0e0ff'
  secondary-fixed-dim: '#bdc2ff'
  on-secondary-fixed: '#000767'
  on-secondary-fixed-variant: '#343d96'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c7'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#fff9e9'
  on-background: '#1e1c10'
  surface-variant: '#e8e2cf'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  title-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  data-tabular:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-xs:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  margin-mobile: 16px
  gutter: 12px
---

## Brand & Style

The design system is engineered for clarity, speed, and precision. It targets professional drivers, commuters, and logistics analysts who require high-density information without cognitive overload. The aesthetic is "Map-Centric Modernism"—a blend of high-utility cartographic interfaces and clean, contemporary mobile UI.

The brand personality is authoritative yet accessible, mirroring the reliability of a physical compass. It utilizes a **Corporate / Modern** style, characterized by a structured information hierarchy, generous whitespace to separate data-rich views, and a sophisticated use of depth to prioritize real-time navigational elements over background telemetry. The emotional response is one of confidence and control, ensuring users feel guided rather than overwhelmed by complex route data.

## Colors

The palette is anchored by the high-visibility **Kakao Yellow**, used sparingly for primary actions and active route highlights to ensure maximum contrast against the **Deep Map Blue** (#1A237E). This blue serves as the foundational color for navigation bars, headers, and primary data containers, providing a professional and stable backdrop.

Semantic coloring is strictly tied to distance and duration analysis:
- **Success/Short:** A forest green for efficient, short-haul routes.
- **Warning/Medium:** A burnt orange for moderate distances requiring more resources.
- **Danger/Long:** A deep red for long-haul routes or significant delays.

The background uses a "Paper White" (#FFFFFF) for primary surfaces and "Asphalt Gray" (#F5F5F5) for secondary background layers to maintain a clean, map-inspired feel.

## Typography

This design system utilizes **Inter** for its exceptional legibility at small sizes and its neutral, systematic character. The typography is optimized for "glanceability"—the ability to read critical data points while in motion.

Special attention is given to **Tabular Figures**. For all route data, coordinates, and time estimates, the `tnum` (tabular numbers) OpenType feature must be enabled to ensure digits align vertically in data tables, preventing visual jumping when values update in real-time. Headlines use a tighter letter-spacing for a modern, compact look, while labels use increased tracking and uppercase styling for clear categorization.

## Layout & Spacing

The layout follows a **Fluid Grid** model based on a 4px baseline rhythm. On mobile devices, a standard 16px side margin is maintained to ensure content remains clear of bezel interference. 

Information is organized into "Content Blocks" that span the full width of the safe area. In data-heavy views, such as route analysis tables, a 12px gutter is used between columns to maximize horizontal space while maintaining distinct separation between data points. Vertical spacing is generous between different categories of information (24px - 32px) but tight within related data groups (4px - 8px) to reinforce visual grouping.

## Elevation & Depth

This design system uses **Ambient Shadows** to create a sense of functional layering. Depth is not merely decorative; it signals interactability and priority.

- **Level 0 (Base):** The map layer or primary background.
- **Level 1 (Cards):** Subsurface cards for data display. These use a 1px soft border (#E0E0E0) and no shadow to maintain a clean profile.
- **Level 2 (Floating Action):** Primary navigation buttons and "Locate Me" triggers. These use a soft, diffused shadow (0px 4px 12px rgba(0,0,0,0.08)) to appear lifted above the map.
- **Level 3 (Modals/Overlays):** Bottom sheets and route detail panels. These use a more pronounced shadow (0px 8px 24px rgba(0,0,0,0.12)) and a background blur on the map behind them to focus user attention.

## Shapes

The shape language is defined by **Rounded** geometry (0.5rem base radius). This softened approach balances the clinical nature of data tables and maps, making the app feel approachable.

- **Buttons & Inputs:** Use the standard 0.5rem (8px) radius.
- **Feature Cards:** Use 1rem (16px) for a more distinct "container" feel.
- **Bottom Sheets:** Use 1.5rem (24px) on the top corners only to create a seamless, integrated appearance with the bottom of the device.
- **Status Indicators:** Pills and small distance tags are fully rounded (capsule shape) to differentiate them from interactive buttons.

## Components

- **Buttons:** Primary buttons are filled with Kakao Yellow with black text for maximum contrast. Secondary buttons use a Deep Blue outline.
- **Route Cards:** These feature a subtle shadow and contain minimalist route graphics. The left edge of the card should feature a 4px vertical color bar corresponding to the semantic status (Short/Medium/Long).
- **Tab Navigation:** A persistent bottom bar using a blur effect (Glassmorphism) to allow the map to peek through. Active states are indicated by the Deep Blue color and a top-aligned yellow indicator line.
- **Data Tables:** Clean rows with light dividers (#F0F0F0). Use the `data-tabular` typography for all numerical columns.
- **Route Graphics:** Use thin, 2pt strokes with rounded caps. Real-time traffic should be represented by subtle glows rather than heavy saturated lines.
- **Input Fields:** Minimalist design with a focus on the active state—a 2px Kakao Yellow bottom border when focused.