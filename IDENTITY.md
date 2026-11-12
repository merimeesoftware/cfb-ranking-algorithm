# IDENTITY.md — CFB Rankings

Locked design identity. Distilled from [DESIGN.md](DESIGN.md). DESIGN.md remains the fuller design doc and UI journey detail.

## Direction

Night-field / chalk board — turf authority without SaaS blue or purple-gradient clichés. The board should feel like a stadium under lights: deep greens, chalk surfaces, stadium gold for the playoff band only.

## Typography

| Role | Face |
|------|------|
| Brand / headlines / ranks | **Oswald** (display) |
| Body / UI | **Source Sans 3** |

Use tabular nums for tables. Do not use Inter, Roboto, Arial, or system as the brand stack.

## Color tokens

| Token | Value | Use |
|-------|-------|-----|
| Field primary | `#1a3d2e` | Brand, primary actions, headers |
| Field deep | `#0f241b` / `#153226` | Hero wash, sticky nav |
| Chalk | `#eef1ee` | Page surface (not warm cream cliché) |
| Stadium gold | `#c9a227` / `#e8c547` | CFP band, primary CTA accent, week-story rail |
| Ink | `#14241c` | Body text on chalk |

Primary Tailwind scale is anchored on field green (`primary-700` ≈ `#1a3d2e`). Avoid default blue primary and purple badge accents on fan surfaces.

## Composition rules

- **This week first:** On home, the first screen is this week’s rankings board. The homepage is that board, with a link to how the formula works. Choosing a team expands that row in place. It does not open a team page.
- **No hero cards / overlay chips.**
- Week story is **editorial** (rail + type), not admin card chrome.
- Filters: no “Ranking Controls” header bar.

## Motion

- Hero rise (~0.7s) and soft goal-line stripe pulse for presence.
- Spinner / transitions respect `prefers-reduced-motion` (global reduce in `app.css`).

## Grunt test

In ~5 seconds a visitor must grunt:

1. **What?** This week’s CFB rankings board
2. **Better?** Clear takes for the fight, not voter vibes
3. **Next?** See this week’s rankings / jump into the controversy

If visuals bury those answers, simplify — distinctiveness must not cost clarity.
