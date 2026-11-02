# Slide-inspired SolarOpt theme

The reference is `SolarOpt_Axiom_Slide.pdf.pptx`, especially slides 1, 5, 6 and 15. Its slides are flattened images, so there is no separate clean background to extract. A new image recreates the visual direction without including slide text, charts or fake interface elements.

## Assets

- `frontend/src/assets/solar-landscape.jpg`: 1672 × 941, optimized JPEG for desktop.
- `frontend/src/assets/solar-landscape-mobile.jpg`: 900 × 507, optimized JPEG for smaller screens and the sidebar.
- `frontend/src/slide-theme.css`: scenery, forest-green typography, ivory overlays, translucent navigation and responsive styling. Loaded after the existing styles.

The artwork is decorative. It is never used as uploaded roof data, a tracing reference, or a computed solar result. The interactive drawing, simulation and project workflow retain their original behavior.

## Generation

Created with the built-in ImageGen tool. Final prompt:

> Use case: photorealistic-natural. Asset type: clean wide website background for SolarOpt rooftop solar engineering studio. Create a high-resolution landscape background in 16:9 inspired by an eco-energy presentation: a serene Vietnamese lakeside landscape with layered forested mountains and a subtle distant modern city skyline, warm sunrise low at bottom left, pale ivory mint-blue sky occupying the top 60 percent. A beautiful contemporary white and timber house with a dark blue solar panel roof occupies the bottom right quarter, surrounded by lush tropical trees. Soft out-of-focus green leaves frame the upper corners and lower left edge. Editorial architectural photography with gentle luminous atmospheric haze, forest green, light sage, cream white, restrained warm yellow highlights. Composition: preserve generous uncluttered pale negative space throughout the left and center for live dark-green website text; keep house and detailed foliage concentrated toward the right and bottom. No text, no letters, no numbers, no logos, no diagrams, no UI, no frames, no watermarks. This is a new standalone background asset, not a slide or website screenshot.

## Local preview

From `frontend`, run `npm.cmd ci`, then `npm.cmd run dev`. Open the local URL printed by Vite (normally `http://127.0.0.1:5174`). Start the backend with `run_backend.bat` from the repository root for simulation and optimization.

Validation commands: `npm.cmd run typecheck` and `npm.cmd run build`.
