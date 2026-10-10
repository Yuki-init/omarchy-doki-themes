#!/usr/bin/env python3
"""Generate Omarchy themes from Doki Theme master definitions.

usage: gen_doki.py <doki-master-theme dir> <output themes dir>
"""
import colorsys, json, pathlib, re, sys

master = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])

def load_template(name):
    data = json.loads((master / "templates" / f"{name}.colors.template.json").read_text())
    colors = {}
    if "extends" in data:
        colors.update(load_template(data["extends"]))
    colors.update(data["colors"])
    return colors

def hx(c):
    c = c.lstrip("#")[:6]
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))

def to_hex(rgb):
    return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02x}" for v in rgb)

def lum(rgb):
    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)

def hls(rgb):
    return colorsys.rgb_to_hls(*rgb)

def shift_l(rgb, dl):
    h, l, s = hls(rgb)
    return colorsys.hls_to_rgb(h, max(0, min(1, l + dl)), s)

def ensure_contrast(rgb, bg, dark, minimum=3.0):
    step = 0.02 if dark else -0.02
    for _ in range(50):
        if contrast(rgb, bg) >= minimum:
            break
        rgb = shift_l(rgb, step)
    return rgb

def hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)

FALLBACK_DARK = {"red": "#ff5f87", "orange": "#ffa25f", "yellow": "#f8e27a", "green": "#5fe08a",
                 "cyan": "#6fe0ea", "blue": "#6fa8ff", "magenta": "#d58cff"}
FALLBACK_LIGHT = {"red": "#d21f4f", "orange": "#c9601a", "yellow": "#a88400", "green": "#2e9a4a",
                  "cyan": "#11899a", "blue": "#2766d1", "magenta": "#a043c9"}
TARGET_HUES = {"red": 350, "orange": 28, "yellow": 52, "green": 125, "cyan": 185, "blue": 220, "magenta": 290}
PALETTE_KEYS = ["accentColor", "keywordColor", "stringColor", "classNameColor", "constantColor",
                "htmlTagColor", "keyColor", "startColor", "stopColor", "iconAccent", "iconAccentCompliment",
                "iconBaseBlend", "iconSecondaryBlend", "iconBlendCompliment", "iconDiversification",
                "dokiLogoAccent", "infoForeground", "errorColor", "terminal.ansiRed", "terminal.ansiGreen",
                "terminal.ansiYellow", "terminal.ansiBlue", "terminal.ansiMagenta", "terminal.ansiCyan"]

def pick(slot, candidates, used, dark):
    target = TARGET_HUES[slot]
    best, best_d = None, 22
    for c in candidates:
        h, l, s = hls(c)
        if s < 0.35 or not (0.25 < l < 0.9) or c in used:
            continue
        d = hue_dist(h * 360, target)
        if d < best_d:
            best, best_d = c, d
    return best or hx((FALLBACK_DARK if dark else FALLBACK_LIGHT)[slot])

def icon_theme(accent):
    h, l, s = hls(accent)
    h *= 360
    if s < 0.2:
        return "Yaru-grey" if False else "Yaru-dark"
    for limit, name in [(15, "Yaru-red"), (40, "Yaru"), (65, "Yaru-yellow"), (95, "Yaru-olive"),
                        (150, "Yaru-sage"), (195, "Yaru-prussiangreen"), (250, "Yaru-blue"),
                        (290, "Yaru-purple"), (340, "Yaru-magenta"), (361, "Yaru-red")]:
        if h < limit:
            return name

def slug(name):
    return "doki-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

templates = {True: load_template("dark"), False: load_template("light")}
manifest = []

for path in sorted(master.glob("definitions/**/*.master.definition.json")):
    d = json.loads(path.read_text())
    dark = d["dark"]
    c = dict(templates[dark])
    c.update(d["colors"])
    col = {k: hx(v) for k, v in c.items() if isinstance(v, str) and v.startswith("#")}

    bg = col["baseBackground"]
    fg = col.get("foregroundColorEditor") if "foregroundColorEditor" in d["colors"] else col["foregroundColor"]
    fg = ensure_contrast(fg, bg, dark, 7.0)
    dir_ = -1 if dark else 1  # direction toward "darker" surfaces in each mode
    candidates = [col[k] for k in PALETTE_KEYS if k in col]

    ansi, used = {}, set()
    for slot in ["red", "yellow", "green", "cyan", "blue", "magenta", "orange"]:
        chosen = pick(slot, candidates, used, dark)
        used.add(chosen)
        ansi[slot] = ensure_contrast(chosen, bg, dark, 3.0 if dark else 3.5)
    brown = shift_l(ansi["orange"], -0.25 if dark else -0.15)

    accent = ensure_contrast(col["accentColor"], bg, dark, 2.5)
    theme = {
        "mode": "dark" if dark else "light",
        "accent": accent,
        "selection": col["selectionBackground"],
        "muted": col["comments"],
        "background": bg,
        "dark_background": shift_l(bg, 0.03 * dir_),
        "darker_background": shift_l(bg, 0.06 * dir_),
        "lighter_background": col.get("secondaryBackground", shift_l(bg, -0.05 * dir_)),
        "foreground": fg,
        "dark_foreground": col.get("lineNumberColor", col["comments"]),
        "light_foreground": col["foregroundColor"],
        "bright_foreground": ensure_contrast(col.get("selectionForeground", fg), bg, dark, 7.0),
        **{k: ansi[k] for k in ["red", "yellow", "orange", "green", "cyan", "blue", "magenta"]},
        "brown": brown,
        **{f"bright_{k}": shift_l(ansi[k], 0.08 if dark else -0.06)
           for k in ["red", "yellow", "green", "cyan", "blue", "magenta"]},
    }

    lines = [f"# Doki Theme: {d['group']} - {d['name']}", f'mode = "{theme.pop("mode")}"', ""]
    for i, (k, v) in enumerate(theme.items()):
        lines.append(f'{k} = "{to_hex(v)}"')
        if k in ("muted", "lighter_background", "bright_foreground", "brown"):
            lines.append("")
    name = slug(d["name"])
    tdir = out / name
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "colors.toml").write_text("\n".join(lines).rstrip() + "\n")
    (tdir / "icons.theme").write_text(icon_theme(col["accentColor"]) + "\n")

    stickers = [s["name"] for s in d.get("stickers", {}).values() if "spicy" not in s["name"]]
    manifest.append({"slug": name, "name": d["name"], "group": d["group"], "dark": dark, "wallpapers": stickers})

(out / "doki-manifest.json").write_text(json.dumps(manifest, indent=2))
print(f"generated {len(manifest)} themes")
