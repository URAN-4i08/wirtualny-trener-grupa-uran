---
name: Cyber Trener
colors:
  surface: '#10131a'
  surface-dim: '#10131a'
  surface-bright: '#363941'
  surface-container-lowest: '#0b0e15'
  surface-container-low: '#191b23'
  surface-container: '#1d2027'
  surface-container-high: '#272a31'
  surface-container-highest: '#32353c'
  on-surface: '#e1e2ec'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#e1e2ec'
  inverse-on-surface: '#2e3038'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#10131a'
  on-background: '#e1e2ec'
  surface-variant: '#32353c'
typography:
  h1:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  h2:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  h3:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin: 32px
  container-max: 1280px
---

## Brand & Style

This design system is engineered to evoke a sense of high-performance intelligence and futuristic vitality. The brand personality is "The Elite Digital Partner"—expert, motivating, and technically superior. It targets fitness enthusiasts and athletes who value data-driven progress and cutting-edge technology.

The visual style merges **Glassmorphism** with a **High-Tech SaaS** aesthetic. It relies on deep spatial depth, utilizing semi-transparent layers and vibrant neon accents to simulate a digital cockpit or a futuristic laboratory environment. The interface should feel fast, responsive, and immersive, moving away from flat design toward a multi-layered, luminous experience.

## Colors

The palette is anchored in a "Deep Space" background to provide maximum contrast for neon elements. 

- **Primary (Neon Blue):** Used for primary actions, progress indicators, and core AI interactions.
- **Secondary (Violet):** Used for secondary highlights, personal records, and data visualization gradients.
- **Surface Grays:** Dark slates are used for card backgrounds to maintain depth without breaking the dark-mode immersion.
- **Glows:** Active states must utilize a 20px blur of the primary or secondary color at 40% opacity to create a "light-emitting" effect.

## Typography

The typography strategy uses **Space Grotesk** for headings to inject a technical, futuristic edge. Its geometric forms resonate with the AI-driven nature of the application. 

For all functional text, body copy, and data readouts, **Inter** is used for its superior legibility and neutral tone, ensuring that complex fitness metrics remain easy to digest. Use uppercase labels with slight letter spacing for category headers (e.g., "TRENING", "STATYSTYKI") to reinforce the dashboard aesthetic.

## Layout & Spacing

The design system employs a **12-column fixed grid** for desktop and a single-column fluid layout for mobile. A 4px baseline grid ensures vertical rhythm.

- **Generous Breathing Room:** Use large internal padding within cards (min 24px) to prevent the high-tech elements from feeling cluttered.
- **Information Density:** For data-heavy views (like workout logs), use a compact 8px spacing between line items, but maintain wide margins around the primary container.
- **Dynamic Grouping:** Use auto-layout with consistent gaps of 16px or 32px to create clear visual clusters of information.

## Elevation & Depth

Hierarchy is established through **Glassmorphism and Tonal Layering** rather than traditional drop shadows.

1.  **Base Layer:** The background (#0f172a) acts as the foundation.
2.  **Mid Layer (Cards):** Semi-transparent surfaces (#1e293b at 80% opacity) with a `backdrop-filter: blur(12px)`.
3.  **Top Layer (Modals/Popovers):** Higher transparency with a subtle 1px inner border (border-white at 10% opacity) to catch "light" at the edges.
4.  **Active Depth:** When an element is focused, apply a "Neon Glow"—a soft, diffused outer shadow using the primary neon blue (#3b82f6) instead of black.

## Shapes

The shape language is "Hyper-Rounded." This softens the aggressive high-tech color palette, making the AI feel approachable and modern.

- **Standard Cards:** Use `rounded-xl` (1.5rem / 24px) for a soft, premium feel.
- **Buttons & Inputs:** Use `rounded-lg` (1rem / 16px) to maintain consistency with the cards while appearing more functional.
- **Progress Bars:** Use fully pill-shaped (rounded-full) containers for a sleek, kinetic look.

## Components

- **Buttons (Przyciski):** Primary buttons feature a subtle linear gradient (Neon Blue to Violet) with white text. Hover states trigger an increased outer glow. Secondary buttons use a ghost style with a 1px solid border.
- **Chips (Tagi):** Small, high-contrast badges for muscle groups or workout types (e.g., "Klatka piersiowa", "Interwały"). Use dark backgrounds with bright text.
- **Inputs (Pola wprowadzania):** Darker than the card background with a subtle "inner glow" on focus. Placeholder text in Polish should be clear and instructional (e.g., "Wpisz wagę...").
- **Cards (Karty):** The cornerstone of the UI. Must include a 1px border at 10% white opacity to define edges against the dark background.
- **AI Pulse:** A specific component for the AI assistant—a circular glowing element that subtly "breathes" (scales slightly) to indicate the AI is processing data.
- **Metrics Display:** Use large, bold numbers for KPIs (BPM, Kilometry, Kalorie) with the label in a smaller, uppercase Inter font.