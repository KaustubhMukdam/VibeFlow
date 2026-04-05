# Design System Specification: The Nocturnal Editor

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Kinetic Gallery."** We are moving away from the static, boxy layouts of traditional web apps and toward a fluid, editorial experience that feels like a high-end physical magazine viewed through a digital lens. 

To achieve this "Signature" look, we prioritize **intentional asymmetry** and **tonal depth**. Rather than aligning everything to a rigid, predictable grid, we use overlapping elements, varying card heights, and extreme typographic scale contrasts to guide the eye. This system isn't just about dark mode; it’s about "Inky Depth"—creating an environment where content glows and UI elements recede into the shadows.

---

## 2. Colors & Surface Philosophy
The palette is rooted in deep neutrals, punctuated by high-energy neon greens. The goal is "vibrant darkness."

### The "No-Line" Rule
**Prohibit 1px solid borders for sectioning.** Boundaries must be defined solely through background color shifts or subtle tonal transitions. To separate a sidebar from a main feed, use a transition from `surface` to `surface-container-low`. To separate a card from its background, use a shift from `surface-container` to `surface-container-highest`.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. Nesting is the primary method of organization:
- **Base Layer:** `surface` (#0e0e0e)
- **Primary Layout Sections:** `surface-container-low` (#131313)
- **Standard Cards/Components:** `surface-container` (#1a1a1a)
- **Elevated/Interactive States:** `surface-container-highest` (#262626)

### The Glass & Gradient Rule
To prevent the UI from feeling "flat," use Glassmorphism for floating elements (headers, player bars, or modals). Apply a backdrop blur of 20px-40px over a semi-transparent `surface-variant`.
*   **Signature Textures:** Main CTAs and Hero sections should utilize a subtle linear gradient: `primary` (#72fe8f) to `primary-container` (#1cb853) at a 135° angle. This adds "soul" and prevents the neon green from looking like a flat digital placeholder.

---

## 3. Typography
We utilize a dual-sans-serif approach to create an editorial hierarchy. **Plus Jakarta Sans** provides a high-end, geometric feel for headlines, while **Inter** ensures maximum legibility for data-heavy body text.

*   **Display (Plus Jakarta Sans):** Use `display-lg` (3.5rem) with tight letter-spacing (-0.04em) for hero titles. This creates an authoritative, "magazine-cover" impact.
*   **Headline (Plus Jakarta Sans):** Use `headline-md` (1.75rem) for section headers. Ensure there is significant whitespace (at least `spacing-12`) above headlines to allow them to breathe.
*   **Body (Inter):** Use `body-md` (0.875rem) for primary descriptions. Set line-height to 1.6 to maintain an airy feel against the dark background.
*   **Labels (Inter):** Use `label-sm` (0.6875rem) in uppercase with 0.1em letter-spacing for secondary metadata or tags. Use the `on-surface-variant` token (#adaaaa) to de-emphasize.

---

## 4. Elevation & Depth
Depth is achieved through **Tonal Layering** and **Ambient Light**, never through heavy structural lines.

### The Layering Principle
Stacking tiers creates natural lift. Place a `surface-container-lowest` card (absolute black) on a `surface-container-low` section to create an "inset" look, or a `surface-container-highest` card on a `surface` background to create "projection."

### Ambient Shadows
For floating modals or menus, use an extra-diffused shadow: 
*   **X: 0, Y: 20, Blur: 40, Spread: -10.** 
*   **Color:** Use a 6% opacity version of `on-surface` (#ffffff). This mimics a soft glow around the object rather than a harsh drop-shadow.

### The "Ghost Border" Fallback
If accessibility requires a container edge, use a **Ghost Border**: 1px solid `outline-variant` at **15% opacity**. This provides a hint of structure without breaking the seamless "No-Line" philosophy.

---

## 5. Components

### Buttons
*   **Primary:** Filled with the `primary` to `primary-container` gradient. Border-radius: `xl` (3rem). Text: `on-primary` (#005f26).
*   **Secondary:** Ghost style. No background, `outline` token at 20% opacity. On hover, transition to `surface-container-highest`.
*   **Interaction:** On press, scale the button to 0.96 for a tactile "click" sensation.

### Cards & Lists
*   **Cards:** Use `surface-container` with a `lg` (2rem) corner radius. **Forbid dividers.** Separate content using `spacing-4` or `spacing-6`. 
*   **Interactive Cards:** On hover, the background should shift to `surface-bright` (#2c2c2c) and the image inside should scale 5% to create depth.

### Navigation
*   **Sidebar (Desktop):** Use `surface-container-low`. Use active state indicators that are vertical "pills" of `primary` color, but with a `blur-sm` glow effect behind them.
*   **Bottom Nav (Mobile):** Use a glassmorphic background (`surface-variant` at 80% opacity with 24px backdrop blur).

### Inputs
*   **Text Fields:** Use `surface-container-highest` with a `sm` radius. The focus state should not be a border change, but a subtle glow: a 2px outer-glow using `primary` at 30% opacity.

---

## 6. Do's and Don'ts

### Do:
*   **Do** use asymmetrical margins. For example, a wider left margin for headlines than for the grid below to create a "custom-built" feel.
*   **Do** use `primary-dim` for icons that are active but not the primary focus of the page.
*   **Do** prioritize "Negative Space." If a section feels crowded, double the spacing token (e.g., move from `spacing-8` to `spacing-16`).

### Don't:
*   **Don't** use pure white (#ffffff) for long-form body text. Use `on-surface-variant` (#adaaaa) to reduce eye strain in dark mode.
*   **Don't** use 100% opaque borders. They act as "speed bumps" for the user's eyes.
*   **Don't** use standard "Swing" easing for transitions. Use a "Quintic Out" or "Exponential" curve to make the UI feel snappier and more premium.