---
name: Tactical Intelligence Interface
colors:
  surface: '#10131c'
  surface-dim: '#10131c'
  surface-bright: '#353943'
  surface-container-lowest: '#0a0e16'
  surface-container-low: '#181c24'
  surface-container: '#1c2028'
  surface-container-high: '#262a33'
  surface-container-highest: '#31353e'
  on-surface: '#e0e2ee'
  on-surface-variant: '#bcc9cd'
  inverse-surface: '#e0e2ee'
  inverse-on-surface: '#2d303a'
  outline: '#869397'
  outline-variant: '#3d494c'
  surface-tint: '#4cd7f6'
  primary: '#4cd7f6'
  on-primary: '#003640'
  primary-container: '#06b6d4'
  on-primary-container: '#00424f'
  inverse-primary: '#00687a'
  secondary: '#adc6ff'
  on-secondary: '#002e6a'
  secondary-container: '#0566d9'
  on-secondary-container: '#e6ecff'
  tertiary: '#ffb2b7'
  on-tertiary: '#67001b'
  tertiary-container: '#ff7f8b'
  on-tertiary-container: '#7d0023'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#acedff'
  primary-fixed-dim: '#4cd7f6'
  on-primary-fixed: '#001f26'
  on-primary-fixed-variant: '#004e5c'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#ffdadb'
  tertiary-fixed-dim: '#ffb2b7'
  on-tertiary-fixed: '#40000d'
  on-tertiary-fixed-variant: '#92002a'
  background: '#10131c'
  on-background: '#e0e2ee'
  surface-variant: '#31353e'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: 0.05em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.2'
  body-lg:
    fontFamily: JetBrains Mono
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.1em
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '400'
    lineHeight: '1'
    letterSpacing: 0.05em
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
spacing:
  unit: 4px
  gutter: 16px
  margin: 24px
  panel-padding: 12px
---

## Brand & Style
The design system is a tactical sci-fi HUD (Heads-Up Display) designed for high-density information environments. It evokes a sense of advanced computational power, urgency, and technical precision. The aesthetic is rooted in **Futuristic Brutalism**, prioritizing raw data visualization and structural geometry over decorative fluff.

The interface serves as a mission-control hub where every element feels like a functional instrument. It targets developers, power users, and sci-fi enthusiasts who value a "command center" experience. The emotional response is one of hyper-focus, authority, and immersion in a high-stakes digital void.

## Colors
This design system operates exclusively in a high-contrast dark mode. 

- **The Void (#050810):** The primary background color, providing a deep, infinite base.
- **Data Cyan (#06B6D4):** The primary interactive and status color. Used for text, primary borders, and the core of glow effects.
- **Link Blue (#3B82F6):** Secondary accent for data visualization, secondary buttons, and depth-layering.
- **Alert Red (#F43F5E):** Reserved for critical errors, system warnings, and destructive actions.
- **Neutral Tiers:** Use semi-transparent whites (e.g., `rgba(255, 255, 255, 0.1)`) for subtle grid lines and non-essential metadata.

All interactive elements should utilize a "neon-bleed" glow effect using the primary cyan color to simulate a light-emitting phosphor display.

## Typography
The typography is split between two distinct roles:
1.  **Command Headers (Space Grotesk):** Angular and wide, used for titles and primary navigation. Always set in uppercase to reinforce the HUD authority.
2.  **Telemetry Data (JetBrains Mono):** A monospaced font used for all body text, status readouts, and numerical data. It ensures vertical alignment across columns of data.

**Formatting Rules:**
- Use "label-caps" for all button labels and input headers.
- Use "data-mono" for timestamps, coordinates, and background status indicators.
- Avoid italics; emphasize text using weight shifts or color changes to Data Cyan.

## Layout & Spacing
The layout follows a **Fixed Modular Grid** system. Screens should be divided into quadrants or defined "Panels." 

- **Grid:** Use a 12-column grid for desktop with 16px gutters. Panels should snap to the grid.
- **Density:** High. Content is packed tightly to mimic a cockpit environment.
- **Safe Zones:** Maintain a 24px margin around the screen edges where critical "System Status" text (time, battery, connection) resides.
- **Adaptation:** On mobile, panels stack vertically. The central "Voice Orb" or primary status visual should remain pinned to the top or center-focus.

## Elevation & Depth
Depth is created through **Luminance and Layering** rather than realistic shadows.

- **Background:** The base layer is #050810.
- **Panels:** UI containers use a slightly lighter #0A0F1D surface with a 1px border of #06B6D4 at 20% opacity.
- **Glow (Elevation):** Active or hovered elements emit a Cyan glow (`box-shadow: 0 0 15px rgba(6, 182, 212, 0.4)`).
- **Scanning Lines:** A subtle, animated scan-line overlay (horizontal line at 2% opacity) moves across the screen to add "hardware" texture.
- **Glassmorphism:** Use only for transient overlays (modals), with a heavy background blur (20px) and a tinted #06B6D4 border.

## Shapes
The shape language is strictly **Geometric and Angular**.

- **Corners:** Use 0px radius for almost all containers and buttons to maintain a technical, "milled metal" feel.
- **Corner Brackets:** Panels should feature 4px "L-shaped" brackets in the corners to emphasize framing.
- **The Orb:** The only exception is the central intelligence core, which is perfectly circular and composed of multiple rotating dashed rings.
- **Progress Bars:** Use segmented blocks (e.g., `[|||||||....]`) rather than smooth continuous fills.

## Components
- **Buttons:** Rectangular with 1px borders. Default state is low-opacity cyan text; Hover state fills the button with cyan and changes text to black.
- **Voice Orb:** A multi-layered circular component. Inner core pulses with a gradient glow; outer rings rotate at different speeds with "stuttery" 15-degree increments.
- **Status Indicators:** Use ASCII-inspired markers (e.g., `> ACTIVE`, `[ LOCKED ]`, `:: SYNC`).
- **Input Fields:** Bottom-border only or bracketed corners. Use a blinking block cursor (`_`) for focused states.
- **Segmented Progress:** Divides a bar into 10-20 distinct vertical blocks. Active blocks glow; inactive blocks are dark grey.
- **Terminal Feed:** A scrolling list of monospaced text entries, using a typewriter-style entrance animation for new data strings.
- **Chips:** Small, all-caps tags with a leading dot indicator (e.g., `● SECURE`).