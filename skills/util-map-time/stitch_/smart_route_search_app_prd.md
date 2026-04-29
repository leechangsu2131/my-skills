# 📍 Smart Route Search App (Kakao Maps Version)

A Streamlit-based application providing four types of route analysis using the Kakao Maps API.

## Core Features (Tabs)

| Tab | Feature | Description |
|---|---|---|
| 🚗 **Tab 1** | Single Start → Multiple Places | Calculate distance and time from one starting point to multiple locations (Excel-based). |
| 📊 **Tab 2** | Multiple Starts → Multiple Ends | Matrix calculation for routes between multiple origins and destinations. |
| 📍 **Tab 3** | Optimal Midpoint Search | Find the best meeting point based on participants' locations. |
| 🛣️ **Tab 4** | Waypoint Comparison (A→X→B) | Compare total travel time when visiting different candidate waypoints between A and B. |

## Technical Setup
- **API:** Kakao Maps REST API (Place Search + Directions)
- **Framework:** Streamlit
- **Data Input:** Excel files (flexible structure) or direct input.
- **Key Metric:** Total travel time and distance compared to direct routes.

## Design Goals
- Clean, map-inspired aesthetic.
- Color-coded distance indicators (🟢 <5km, 🟠 5-15km, 🔴 >15km).
- Tabbed navigation for distinct features.
- User-friendly configuration for API keys and data mapping.