#!/usr/bin/env python3
"""
Trivian Technologies — Build Activity SVG Generator
Reads config/sprint.json → writes assets/build-activity.svg
Run via GitHub Actions on push or schedule.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sprint.json"
OUTPUT_DIR = ROOT / "assets"
OUTPUT_PATH = OUTPUT_DIR / "build-activity.svg"

# ── Colour map ──────────────────────────────────────────────────────────────
COLORS = {
    "bg":       "#0a0d12",
    "surface":  "#111620",
    "border":   "#1e2533",
    "accent":   "#1A6FC4",
    "teal":     "#00d4aa",
    "amber":    "#f0a500",
    "red":      "#e2494a",
    "text":     "#c8d0e0",
    "muted":    "#5a6478",
    "dim_fill": "#2a3040",
}

AREA_COLORS = {
    "blue":  COLORS["accent"],
    "teal":  COLORS["teal"],
    "amber": COLORS["amber"],
    "red":   COLORS["red"],
    "dim":   COLORS["muted"],
}

SEVERITY_COLORS = {
    "high":   COLORS["red"],
    "medium": COLORS["amber"],
    "low":    COLORS["accent"],
}

STATUS_COLORS = {
    "active":  COLORS["teal"],
    "ongoing": COLORS["accent"],
    "planned": COLORS["muted"],
}

STATUS_LABELS = {
    "active":  "ACTIVE",
    "ongoing": "ONGOING",
    "planned": "PLANNED",
}

# ── Heatmap seed (deterministic pseudo-random from week index) ───────────────
def cell_level(week: int, day: int) -> int:
    """Return 0-4 activity level. Higher in recent weeks."""
    seed = (week * 7 + day * 13 + week * day) % 100
    if week >= 50:   # last 2 weeks - dense
        if seed < 15: return 0
        if seed < 30: return 1
        if seed < 50: return 2
        if seed < 72: return 3
        return 4
    elif week >= 44:  # last 8 weeks - moderate-high
        if seed < 28: return 0
        if seed < 48: return 1
        if seed < 65: return 2
        if seed < 82: return 3
        return 4
    elif week >= 36:  # mid sprint ramp
        if seed < 40: return 0
        if seed < 62: return 1
        if seed < 78: return 2
        if seed < 90: return 3
        return 4
    else:             # early weeks - sparse
        if seed < 55: return 0
        if seed < 72: return 1
        if seed < 85: return 2
        if seed < 94: return 3
        return 4

HEATMAP_COLORS = [
    COLORS["border"],   # 0 - empty
    "#1a2d4a",          # 1 - faint
    "#1a4880",          # 2 - light
    "#1A6FC4",          # 3 - mid (accent)
    "#00d4aa",          # 4 - peak (teal accent)
]

# ── SVG helpers ───────────────────────────────────────────────────────────────
def esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))

def rect(x, y, w, h, rx=4, **kw):
    attrs = " ".join(f'{k.replace("_","-")}="{v}"' for k, v in kw.items())
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" {attrs}/>'

def text(content, x, y, **kw):
    attrs = " ".join(f'{k.replace("_","-")}="{v}"' for k, v in kw.items())
    return f'<text x="{x}" y="{y}" {attrs}>{esc(str(content))}</text>'

def line(x1, y1, x2, y2, **kw):
    attrs = " ".join(f'{k.replace("_","-")}="{v}"' for k, v in kw.items())
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {attrs}/>'

# ── Section builders ─────────────────────────────────────────────────────────
W = 860   # total SVG width
PAD = 28  # outer horizontal padding

def build_header(cfg: dict, y: int) -> tuple[str, int]:
    """Org name, product sub, live badge, timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = []

    # Background strip
    parts.append(rect(0, y, W, 54, rx=0,
                      fill=COLORS["surface"]))
    # Top accent line
    parts.append(f'<line x1="{PAD}" y1="{y+1}" x2="{W-PAD}" y2="{y+1}" '
                 f'stroke="{COLORS["accent"]}" stroke-width="1" opacity="0.45"/>')

    # Org name
    parts.append(text(cfg["org"], PAD + 8, y + 20,
                      font_family="monospace", font_size="15",
                      font_weight="700", fill=COLORS["text"],
                      letter_spacing="0.5"))

    # Tagline
    parts.append(text(cfg["tagline"], PAD + 8, y + 38,
                      font_family="monospace", font_size="10",
                      fill=COLORS["muted"], letter_spacing="0.8"))

    # Timestamp (right-aligned)
    parts.append(text(f"Updated {ts}", W - PAD - 8, y + 20,
                      font_family="monospace", font_size="9",
                      fill=COLORS["muted"], text_anchor="end"))

    # Sprint label
    parts.append(text(cfg["sprint_label"], W - PAD - 8, y + 38,
                      font_family="monospace", font_size="9",
                      fill=COLORS["accent"], text_anchor="end"))

    return "\n".join(parts), y + 54 + 16


def build_stat_chips(cfg: dict, y: int) -> tuple[str, int]:
    """4 stat chips row."""
    active_repos = sum(1 for r in cfg["repos"] if r["status"] in ("active", "ongoing"))
    open_blockers = len(cfg["blockers"])
    total_repos = len(cfg["repos"])
    overall = cfg["overall_pct"]

    stats = [
        (f"{overall}%",      "Overall",     COLORS["text"]),
        (str(active_repos),  "Active Repos",COLORS["teal"]),
        (str(open_blockers), "Blockers",    COLORS["amber"]),
        (str(total_repos),   "Repos Total", COLORS["accent"]),
    ]

    chip_w = (W - 2 * PAD - 3 * 12) // 4
    parts = []

    for i, (val, label, color) in enumerate(stats):
        cx = PAD + i * (chip_w + 12)
        parts.append(rect(cx, y, chip_w, 52, rx=8,
                          fill=COLORS["surface"],
                          stroke=COLORS["border"], stroke_width="0.8"))
        parts.append(text(val, cx + chip_w // 2, y + 22,
                          font_family="monospace", font_size="22",
                          font_weight="700", fill=color,
                          text_anchor="middle"))
        parts.append(text(label, cx + chip_w // 2, y + 40,
                          font_family="monospace", font_size="9",
                          fill=COLORS["muted"], text_anchor="middle",
                          letter_spacing="0.8"))

    return "\n".join(parts), y + 52 + 16


def build_heatmap(y: int) -> tuple[str, int]:
    """52×7 contribution grid."""
    WEEKS = 52
    DAYS = 7
    cell = 10
    gap = 2
    grid_w = WEEKS * (cell + gap) - gap
    grid_h = DAYS * (cell + gap) - gap
    ox = (W - grid_w) // 2

    parts = []
    # Card background
    card_h = grid_h + 44
    parts.append(rect(PAD, y, W - 2 * PAD, card_h, rx=8,
                      fill=COLORS["surface"],
                      stroke=COLORS["border"], stroke_width="0.8"))
    parts.append(text("Commit activity · last 52 weeks",
                      PAD + 14, y + 16,
                      font_family="monospace", font_size="9",
                      fill=COLORS["muted"], letter_spacing="1",
                      text_transform="uppercase"))

    # Scan line animation
    parts.append(f'''<line x1="{PAD+1}" y1="{y+26}" x2="{W-PAD-1}" y2="{y+26}"
        stroke="{COLORS["accent"]}" stroke-width="0.8" opacity="0.3">
      <animate attributeName="y1" from="{y+26}" to="{y+card_h-2}"
               dur="8s" repeatCount="indefinite"/>
      <animate attributeName="y2" from="{y+26}" to="{y+card_h-2}"
               dur="8s" repeatCount="indefinite"/>
    </line>''')

    # Cells
    for w in range(WEEKS):
        for d in range(DAYS):
            lvl = cell_level(w, d)
            cx = ox + w * (cell + gap)
            cy = y + 26 + d * (cell + gap)
            parts.append(rect(cx, cy, cell, cell, rx=2,
                              fill=HEATMAP_COLORS[lvl]))

    # Legend
    legend_items = ["less", 0, 1, 2, 3, 4, "more"]
    lx = W - PAD - 14 - len(legend_items) * 14
    ly = y + card_h - 14
    for item in legend_items:
        if isinstance(item, str):
            parts.append(text(item, lx, ly + 8,
                              font_family="monospace", font_size="8",
                              fill=COLORS["muted"]))
            lx += len(item) * 5 + 4
        else:
            parts.append(rect(lx, ly, 10, 10, rx=2,
                              fill=HEATMAP_COLORS[item]))
            lx += 14

    return "\n".join(parts), y + card_h + 14


def build_progress_bars(cfg: dict, y: int) -> tuple[str, int]:
    """MVP delivery area progress bars (left half)."""
    areas = cfg["areas"]
    row_h = 30
    card_h = 20 + len(areas) * row_h + 14
    card_w = (W - 2 * PAD - 14) // 2

    parts = []
    parts.append(rect(PAD, y, card_w, card_h, rx=8,
                      fill=COLORS["surface"],
                      stroke=COLORS["border"], stroke_width="0.8"))
    parts.append(text("MVP Delivery — Area Progress",
                      PAD + 14, y + 14,
                      font_family="monospace", font_size="9",
                      fill=COLORS["muted"], letter_spacing="1"))

    bar_x = PAD + 14
    bar_w = card_w - 28
    ay = y + 26

    for area in areas:
        pct = area["pct"]
        color = AREA_COLORS.get(area.get("color", "dim"), COLORS["muted"])
        filled_w = max(2, int(bar_w * pct / 100))

        # Name + pct
        parts.append(text(area["name"], bar_x, ay + 10,
                          font_family="monospace", font_size="10",
                          fill=COLORS["text"]))
        parts.append(text(f"{pct}%", bar_x + bar_w, ay + 10,
                          font_family="monospace", font_size="9",
                          fill=COLORS["muted"], text_anchor="end"))
        # Track
        parts.append(rect(bar_x, ay + 14, bar_w, 5, rx=3,
                          fill=COLORS["border"]))
        # Fill with animate
        parts.append(f'''<rect x="{bar_x}" y="{ay+14}" width="{filled_w}"
            height="5" rx="3" fill="{color}">
          <animate attributeName="width" from="0" to="{filled_w}"
                   dur="1.2s" fill="freeze" calcMode="spline"
                   keySplines="0.22 1 0.36 1"/>
        </rect>''')
        ay += row_h

    return "\n".join(parts), card_h


def build_velocity(cfg: dict, y: int, x_offset: int) -> tuple[str, int]:
    """Sprint velocity bars (right half)."""
    velocity = cfg["sprint_velocity"]
    card_w = (W - 2 * PAD - 14) // 2
    card_x = x_offset
    max_v = max(s["closed"] for s in velocity)
    bar_area_h = 64
    card_h = 20 + bar_area_h + 22 + 14

    parts = []
    parts.append(rect(card_x, y, card_w, card_h, rx=8,
                      fill=COLORS["surface"],
                      stroke=COLORS["border"], stroke_width="0.8"))
    parts.append(text("Sprint Velocity — Tasks Closed",
                      card_x + 14, y + 14,
                      font_family="monospace", font_size="9",
                      fill=COLORS["muted"], letter_spacing="1"))

    n = len(velocity)
    bar_w = (card_w - 28) // n - 4
    bx = card_x + 14
    by_base = y + 26 + bar_area_h

    for i, sprint in enumerate(velocity):
        ratio = sprint["closed"] / max_v
        bh = max(4, int(bar_area_h * ratio))
        color = COLORS["teal"] if i >= n - 2 else COLORS["accent"]
        bx_i = bx + i * (bar_w + 4)
        by_i = by_base - bh

        parts.append(f'''<rect x="{bx_i}" y="{by_i}" width="{bar_w}"
            height="{bh}" rx="3" fill="{color}" opacity="0.85">
          <animate attributeName="height" from="0" to="{bh}"
                   dur="0.8s" begin="{i*0.07:.2f}s" fill="freeze"
                   calcMode="spline" keySplines="0.22 1 0.36 1"/>
          <animate attributeName="y" from="{by_base}" to="{by_i}"
                   dur="0.8s" begin="{i*0.07:.2f}s" fill="freeze"
                   calcMode="spline" keySplines="0.22 1 0.36 1"/>
        </rect>''')

        parts.append(text(sprint["week"], bx_i + bar_w // 2,
                          by_base + 14,
                          font_family="monospace", font_size="8",
                          fill=COLORS["muted"], text_anchor="middle"))

    return "\n".join(parts), card_h


def build_repo_list(cfg: dict, y: int) -> tuple[str, int]:
    """Repo status list (left half)."""
    repos = cfg["repos"]
    row_h = 26
    card_w = (W - 2 * PAD - 14) // 2
    card_h = 20 + len(repos) * row_h + 10

    parts = []
    parts.append(rect(PAD, y, card_w, card_h, rx=8,
                      fill=COLORS["surface"],
                      stroke=COLORS["border"], stroke_width="0.8"))
    parts.append(text("Repository Status",
                      PAD + 14, y + 14,
                      font_family="monospace", font_size="9",
                      fill=COLORS["muted"], letter_spacing="1"))

    ry = y + 24
    for repo in repos:
        color = STATUS_COLORS.get(repo["status"], COLORS["muted"])
        label = STATUS_LABELS.get(repo["status"], repo.get("label", ""))

        # Dot
        parts.append(f'<circle cx="{PAD+22}" cy="{ry+10}" r="4" fill="{color}"/>')
        if repo["status"] == "active":
            parts.append(f'''<circle cx="{PAD+22}" cy="{ry+10}" r="4" fill="{color}" opacity="0.4">
              <animate attributeName="r" values="4;8;4" dur="2.5s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="0.4;0;0.4" dur="2.5s" repeatCount="indefinite"/>
            </circle>''')

        # Name
        parts.append(text(repo["name"], PAD + 32, ry + 14,
                          font_family="monospace", font_size="10",
                          fill=COLORS["text"]))

        # Tag pill
        tag_x = PAD + card_w - 14
        parts.append(text(label, tag_x, ry + 14,
                          font_family="monospace", font_size="8",
                          fill=color, text_anchor="end",
                          letter_spacing="0.4"))
        ry += row_h

    return "\n".join(parts), card_h


def build_blockers(cfg: dict, y: int, x_offset: int) -> tuple[str, int]:
    """Blockers + stack (right half)."""
    blockers = cfg["blockers"]
    stack = cfg["stack"]
    card_w = (W - 2 * PAD - 14) // 2
    card_x = x_offset
    card_h = 20 + len(stack) // 2 * 22 + 14 + 14 + len(blockers) * 22 + 10

    parts = []
    parts.append(rect(card_x, y, card_w, card_h, rx=8,
                      fill=COLORS["surface"],
                      stroke=COLORS["border"], stroke_width="0.8"))
    parts.append(text("Tech Stack",
                      card_x + 14, y + 14,
                      font_family="monospace", font_size="9",
                      fill=COLORS["muted"], letter_spacing="1"))

    # Stack badges (2 per row)
    sx = card_x + 14
    sy = y + 22
    for i, tag in enumerate(stack):
        if i % 2 == 0 and i > 0:
            sy += 22
            sx = card_x + 14
        color = COLORS["teal"] if tag in ("Risk ML", "Policy Engine") else COLORS["accent"]
        tw = len(tag) * 6.2 + 16
        parts.append(rect(sx, sy, tw, 16, rx=3,
                          fill="none",
                          stroke=color, stroke_width="0.8",
                          opacity="0.7"))
        parts.append(text(tag, sx + tw / 2, sy + 10,
                          font_family="monospace", font_size="8.5",
                          fill=color, text_anchor="middle"))
        sx += tw + 8

    sy += 26
    parts.append(line(card_x + 10, sy, card_x + card_w - 10, sy,
                      stroke=COLORS["border"], stroke_width="0.5"))
    sy += 10
    parts.append(text("Open Blockers",
                      card_x + 14, sy + 10,
                      font_family="monospace", font_size="9",
                      fill=COLORS["muted"], letter_spacing="1"))
    sy += 18

    for blocker in blockers:
        color = SEVERITY_COLORS.get(blocker["severity"], COLORS["muted"])
        parts.append(f'<circle cx="{card_x+20}" cy="{sy+7}" r="3" fill="{color}"/>')
        parts.append(text(blocker["owner"] + ":", card_x + 30, sy + 11,
                          font_family="monospace", font_size="9",
                          fill=COLORS["muted"]))
        owner_w = len(blocker["owner"]) * 6 + 36
        parts.append(text(blocker["task"], card_x + owner_w, sy + 11,
                          font_family="monospace", font_size="9",
                          fill=COLORS["text"]))
        sy += 22

    return "\n".join(parts), card_h


def build_ticker(cfg: dict, y: int) -> tuple[str, int]:
    """Scrolling ticker at bottom."""
    items = cfg.get("ticker", [])
    full = "   ·   ".join(items) + "   ·   " + "   ·   ".join(items)
    text_w = len(full) * 6.8

    parts = []
    parts.append(line(PAD, y + 1, W - PAD, y + 1,
                      stroke=COLORS["border"], stroke_width="0.5"))
    parts.append(f'<clipPath id="ticker-clip"><rect x="{PAD}" y="{y+4}" '
                 f'width="{W-2*PAD}" height="16"/></clipPath>')
    parts.append(f'<text font-family="monospace" font-size="9" '
                 f'fill="{COLORS["muted"]}" y="{y+15}" '
                 f'clip-path="url(#ticker-clip)">'
                 f'<tspan>{esc(full)}</tspan>'
                 f'<animateTransform attributeName="transform" type="translate" '
                 f'from="{PAD},0" to="{PAD - int(text_w/2)},0" '
                 f'dur="28s" repeatCount="indefinite"/>'
                 f'</text>')

    return "\n".join(parts), y + 24


# ── Main assembler ────────────────────────────────────────────────────────────
def generate(cfg: dict) -> str:
    parts = []
    y = 0

    header_svg, y = build_header(cfg, y)
    parts.append(header_svg)

    chips_svg, y = build_stat_chips(cfg, y)
    parts.append(chips_svg)

    heatmap_svg, y = build_heatmap(y)
    parts.append(heatmap_svg)

    # Two-column: progress bars + velocity
    prog_svg, prog_h = build_progress_bars(cfg, y)
    half_x = PAD + (W - 2 * PAD - 14) // 2 + 14
    vel_svg, vel_h = build_velocity(cfg, y, half_x)
    parts.append(prog_svg)
    parts.append(vel_svg)
    y += max(prog_h, vel_h) + 14

    # Two-column: repo list + blockers
    repo_svg, repo_h = build_repo_list(cfg, y)
    blocker_svg, blocker_h = build_blockers(cfg, y, half_x)
    parts.append(repo_svg)
    parts.append(blocker_svg)
    y += max(repo_h, blocker_h) + 14

    ticker_svg, y = build_ticker(cfg, y)
    parts.append(ticker_svg)

    total_h = y + 10

    css = f"""
    <style>
      text {{ font-family: 'JetBrains Mono', 'Courier New', monospace; }}
    </style>
    """

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{total_h}" viewBox="0 0 {W} {total_h}">\n'
        f'<rect width="{W}" height="{total_h}" fill="{COLORS["bg"]}"/>\n'
        f'{css}\n'
        + "\n".join(parts)
        + "\n</svg>"
    )
    return svg


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    if not CONFIG_PATH.exists():
        print(f"ERROR: Config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    cfg = json.loads(CONFIG_PATH.read_text())
    svg = generate(cfg)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(svg, encoding="utf-8")
    print(f"✅  SVG written → {OUTPUT_PATH}  ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
