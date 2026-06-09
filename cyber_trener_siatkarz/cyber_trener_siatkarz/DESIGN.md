---
name: Cyber-Trener Siatkarz
colors:
  surface: '#1c110b'
  surface-dim: '#1c110b'
  surface-bright: '#45362f'
  surface-container-lowest: '#160c06'
  surface-container-low: '#251913'
  surface-container: '#291d16'
  surface-container-high: '#352720'
  surface-container-highest: '#40322a'
  on-surface: '#f6ded3'
  on-surface-variant: '#e0c0b1'
  inverse-surface: '#f6ded3'
  inverse-on-surface: '#3c2d26'
  outline: '#a78b7d'
  outline-variant: '#584237'
  surface-tint: '#ffb690'
  primary: '#ffb690'
  on-primary: '#552100'
  primary-container: '#f97316'
  on-primary-container: '#582200'
  inverse-primary: '#9d4300'
  secondary: '#7bd0ff'
  on-secondary: '#00354a'
  secondary-container: '#00a6e0'
  on-secondary-container: '#00374d'
  tertiary: '#d3bbff'
  on-tertiary: '#3f008d'
  tertiary-container: '#ad83ff'
  on-tertiary-container: '#410091'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbca'
  primary-fixed-dim: '#ffb690'
  on-primary-fixed: '#341100'
  on-primary-fixed-variant: '#783200'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#ebddff'
  tertiary-fixed-dim: '#d3bbff'
  on-tertiary-fixed: '#260059'
  on-tertiary-fixed-variant: '#5b00c5'
  background: '#1c110b'
  on-background: '#f6ded3'
  surface-variant: '#40322a'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  kpi-value:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 40px
  xl: 64px
  sidebar-width: 260px
  sidebar-collapsed: 80px
  container-max: 1440px
---

## Brand & Style
The design system for this virtual volleyball coach app is built on a "Professional Athletic Performance" aesthetic. It moves away from cliché "cyber" aesthetics (no neon/glitch effects) in favor of a clean, data-driven environment that mirrors high-end sports analytics software.

The mood is focused, authoritative, and energetic. It leverages a **Modern Glassmorphic** style—using deep-sea navies and subtle translucency to create layers of information without cluttering the visual field. This approach ensures the athlete's performance data and video feedback remain the focal point.

## Colors
The palette utilizes a "Deep Space" hierarchy to maximize contrast for data visualization.
- **Backgrounds:** The primary foundation is a deep navy, providing a low-strain environment for reviewing match footage.
- **Accents:** Orange is reserved strictly for high-priority actions (CTA) and active states (current drills). Light Blue and Purple serve as secondary identifiers for data categories or specific coaching modules.
- **Glassmorphism:** Surface containers use a subtle white border (10% opacity) and 12px backdrop blur to lift content off the deep background, simulating a tactical glass overlay.

## Typography
The system uses a pairing of **Space Grotesk** for headlines and **Inter** for body text. 
- **Headlines:** Space Grotesk's technical, geometric terminals provide the "Cyber" feel in a sophisticated, professional manner. Use it for page titles, section headers, and high-impact numbers.
- **Body & Labels:** Inter provides maximum legibility for long-form feedback and technical descriptions.
- **KPI Values:** Specifically utilize Space Grotesk for metric displays (e.g., vertical jump height, strike speed) to emphasize the data-centric nature of the application.

## Layout & Spacing
The system employs a **12-column fluid grid** for the main dashboard, with fixed safe margins of 24px on desktop and 16px on mobile.

- **Sidebar:** A collapsible navigation rail is anchored to the left. When expanded, it pushes content; when collapsed, it provides clear iconic shortcuts.
- **The 8px Rule:** All spacing, padding, and margins must be multiples of 8px (or 4px for tight internal component spacing) to maintain a rigid, athletic structure.
- **Responsive Behavior:** On mobile, KPI cards stack vertically into a single column. The Coaches Banner maintains a 16:9 aspect ratio to ensure video feedback is never cropped.

## Elevation & Depth
Depth is created through **Tonal Layering** and **Blur**, rather than traditional heavy shadows.
- **Level 0 (Base):** Deep Navy background.
- **Level 1 (Cards/Surfaces):** Semi-transparent glass containers. They should feature a 1px solid border at 10% white opacity to define the edges against the dark background.
- **Level 2 (Modals/Popovers):** Higher opacity background blur (20px+) with a slight drop shadow (0 10px 30px rgba(0,0,0,0.5)) to isolate the interaction.
- **Interactive States:** Buttons and active tiles use an outer glow (primary orange) to signify "active energy."

## Shapes
The shape language combines generous outer radii with tighter inner radii to create a "contained" professional look.
- **Containers:** Dashboard cards use `1rem` (16px) rounding to soften the technical data.
- **Interactive Elements:** Buttons and Input fields use `0.75rem` (12px) rounding, creating a distinct visual difference from the larger layout containers.
- **Readiness Tiles:** Perfect squares or circles depending on the specific metric, ensuring they feel like "status lamps" on a cockpit.

## Components
- **Buttons:** Primary buttons use a solid Orange fill with white text. Secondary buttons are "Ghost" style with an Orange border and subtle hover fill.
- **KPI Cards:** Feature a top-aligned label (Inter, 12px, Uppercase) and a large, centered value (Space Grotesk, 36px). Trend indicators (up/down arrows) are placed in the bottom right corner.
- **Readiness Tiles:** Small, status-indicative squares. Color-coded (Green for "Ready", Red for "Fatigued", Gray for "No Data"). They should include a subtle inner pulse animation for the current day.
- **Coaches Banner:** High-visibility overlay. Use a gradient scrim (bottom-to-top) over video content to ensure text legibility. Action buttons on video overlays should use high-contrast white blurs.
- **Charts:** Use the Secondary Accent (Light Blue) for primary data sets and Purple for comparisons. Grid lines within charts should be low-contrast (5% white) to keep the UI clean.
- **Sidebar:** Navy background (#0B1426) with active states highlighted by a vertical Orange strip on the left edge of the menu item.