# DESIGN.md — CFB Rankings

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

- **Brand first:** On home, “CFB Rankings” is a hero-level signal — not only nav text.  
- **One composition** in the first viewport: brand, one headline, one supporting line, one CTA group, field atmosphere.  
- **No hero cards / overlay chips.**  
- **Board below the fold** via primary CTA → `#board` (smooth scroll + focus Find your team).  
- Week story is **editorial** (rail + type), not admin card chrome.  
- Filters: no “Ranking Controls” header bar.

## Motion

- Hero rise (~0.7s) and soft goal-line stripe pulse for presence.  
- Spinner / transitions respect `prefers-reduced-motion` (global reduce in `app.css`).

## Grunt test (home)

In ~5 seconds a visitor must grunt:

1. **What?** This week’s CFB rankings board  
2. **Better?** Clear takes for the fight, not voter vibes  
3. **Next?** See this week’s rankings / jump into the controversy  

If visuals bury those answers, simplify — distinctiveness must not cost clarity.

## Reference

- StoryBrand plan: `docs/superpowers/specs/2026-08-14-storybrand-frontend-plan.md`  
- Copy deck: `docs/superpowers/specs/2026-08-14-storybrand-copy-deck.md`  
- Audit sketch: `docs/superpowers/specs/2026-08-01-frontend-audit.md` §5.10  
