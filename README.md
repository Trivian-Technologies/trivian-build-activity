# trivian-build-activity

> Auto-generated SVG build status widget for the Trivian Technologies GitHub org profile.
> Edit `config/sprint.json` → push → SVG regenerates automatically within ~60 seconds.

---

## Embed in your org profile README

Add this to `.github/profile/README.md` in the **Trivian-Technologies** org:

```markdown
<p align="center">
  <img
    src="https://raw.githubusercontent.com/Trivian-Technologies/trivian-build-activity/main/assets/build-activity.svg"
    alt="Trivian Technologies — Build Activity"
    width="860"
  />
</p>
```

> **Note:** GitHub CDN caches raw files for ~5 minutes. After a push, the updated widget
> will appear within 5–10 minutes on the org profile.

---

## How to update (every sprint)

Open `config/sprint.json` and change **only the values that changed**:

| Field | What to edit |
|---|---|
| `overall_pct` | Recalculate from area totals |
| `areas[].done` | Increment as tasks complete |
| `areas[].pct` | `done / total * 100` (round to int) |
| `sprint_velocity` | Add new week, drop oldest, shift labels |
| `blockers` | Add/remove/update as sprint evolves |
| `repos[].status` | Change `planned` → `active` when work starts |
| `last_updated` | Today's date `YYYY-MM-DD` |
| `sprint_label` | e.g. `"Sprint · April 2026"` |

Push to `main`. The `generate-svg.yml` action fires automatically.
To trigger manually: **Actions → Generate Build Activity SVG → Run workflow**.

---

## Repo structure

```
trivian-build-activity/
├── .github/
│   └── workflows/
│       └── generate-svg.yml   ← GitHub Action (runs on push + schedule)
├── assets/
│   └── build-activity.svg     ← Auto-generated. Do not edit manually.
├── config/
│   └── sprint.json            ← ✏️  THE ONLY FILE YOU NEED TO EDIT
└── scripts/
    └── generate_svg.py        ← Generator (edit only if you want new sections)
```

---

## Local preview

```bash
python scripts/generate_svg.py
# → writes assets/build-activity.svg
# Open in any browser to preview
```

No dependencies beyond Python 3.11 stdlib + `json` (already included).
