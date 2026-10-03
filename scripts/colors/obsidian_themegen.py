#!/usr/bin/env python3
"""
Obsidian iNiR Material You Theme Generator.
Renders the inir-theme.css snippet into the user's Obsidian vault(s).
Supports all Material You schemes (including Monochrome), custom accent colors,
and preset themes from iNiR.
"""

import os
import sys
import json
import re
import importlib

try:
    from materialyoucolor.hct import Hct
    from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors
except ImportError:
    # If run outside venv, re-execute with quickshell venv
    venv_python = os.path.expanduser("~/.local/state/quickshell/.venv/bin/python3")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)
    raise

rgba_to_hex = lambda rgba: "#{:02X}{:02X}{:02X}".format(rgba[0], rgba[1], rgba[2])

SCHEME_MAP = {
    "scheme-content": ("materialyoucolor.scheme.scheme_content", "SchemeContent"),
    "scheme-expressive": ("materialyoucolor.scheme.scheme_expressive", "SchemeExpressive"),
    "scheme-fidelity": ("materialyoucolor.scheme.scheme_fidelity", "SchemeFidelity"),
    "scheme-fruit-salad": ("materialyoucolor.scheme.scheme_fruit_salad", "SchemeFruitSalad"),
    "scheme-monochrome": ("materialyoucolor.scheme.scheme_monochrome", "SchemeMonochrome"),
    "scheme-neutral": ("materialyoucolor.scheme.scheme_neutral", "SchemeNeutral"),
    "scheme-rainbow": ("materialyoucolor.scheme.scheme_rainbow", "SchemeRainbow"),
    "scheme-tonal-spot": ("materialyoucolor.scheme.scheme_tonal_spot", "SchemeTonalSpot"),
    "scheme-vibrant": ("materialyoucolor.scheme.scheme_vibrant", "SchemeVibrant"),
}


def load_scheme_class(scheme_name: str):
    name = (scheme_name or "").strip().lower()
    if not name.startswith("scheme-") and f"scheme-{name}" in SCHEME_MAP:
        name = f"scheme-{name}"
    target = SCHEME_MAP.get(name)
    if target:
        mod_name, cls_name = target
        try:
            mod = importlib.import_module(mod_name)
            return getattr(mod, cls_name)
        except Exception as e:
            print(f"[obsidian_themegen] Warning: Could not import {mod_name}.{cls_name}: {e}", file=sys.stderr)
    from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
    return SchemeTonalSpot


def camel_to_snake(name):
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name).lower()


def snake_to_camel(name):
    parts = name.split("_")
    return parts[0] + "".join(x.capitalize() for x in parts[1:])


def discover_vaults() -> list[str]:
    vaults: list[str] = []
    seen = set()

    def add_vault(path: str):
        if not path:
            return
        expanded = os.path.abspath(os.path.expanduser(path))
        if expanded not in seen and os.path.isdir(expanded):
            seen.add(expanded)
            vaults.append(expanded)

    config_candidates = [
        os.path.expanduser("~/.config/obsidian/obsidian.json"),
        os.path.expanduser("~/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json"),
    ]

    for conf in config_candidates:
        if os.path.isfile(conf):
            try:
                with open(conf, "r") as f:
                    data = json.load(f)
                    for v in data.get("vaults", {}).values():
                        v_path = v.get("path")
                        if v_path:
                            add_vault(v_path)
            except Exception:
                pass

    standard_candidates = [
        "~/Documents/Obsidian",
        "~/Documentos/Obsidiana",
        "~/Obsidian",
        "~/Vault",
        "~/Notas",
    ]
    for cand in standard_candidates:
        expanded = os.path.expanduser(cand)
        if os.path.isdir(os.path.join(expanded, ".obsidian")):
            add_vault(expanded)

    return vaults


def strip_theme(vaults: list[str]):
    for v in vaults:
        snippet_path = os.path.join(v, ".obsidian/snippets/inir-theme.css")
        if os.path.isfile(snippet_path):
            try:
                os.remove(snippet_path)
                print(f"✓ Removed Obsidian snippet: {snippet_path}")
            except Exception as e:
                print(f"[obsidian_themegen] Could not remove {snippet_path}: {e}", file=sys.stderr)

        app_json_path = os.path.join(v, ".obsidian/appearance.json")
        if os.path.isfile(app_json_path):
            try:
                with open(app_json_path, "r") as af:
                    app_data = json.load(af)
                snippets = app_data.get("enabledCssSnippets", [])
                if "inir-theme" in snippets:
                    app_data["enabledCssSnippets"] = [s for s in snippets if s != "inir-theme"]
                    with open(app_json_path, "w") as af:
                        json.dump(app_data, af, indent=2)
                    print(f"✓ Disabled inir-theme snippet in {app_json_path}")
            except Exception as e:
                print(f"[obsidian_themegen] Could not update {app_json_path}: {e}", file=sys.stderr)


def resolve_template_path() -> str | None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "../.."))

    candidates = [
        os.path.expanduser("~/.config/matugen/templates/obsidian/inir-theme.css"),
        os.path.join(repo_root, "dots/.config/matugen/templates/obsidian/inir-theme.css"),
        os.path.join(repo_root, "defaults/matugen/templates/obsidian/inir-theme.css"),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return None


def main():
    vaults = discover_vaults()

    if "--strip" in sys.argv:
        strip_theme(vaults)
        return 0

    state_dir = os.path.expanduser("~/.local/state/quickshell")
    gen_dir = os.path.join(state_dir, "user/generated")
    meta_path = os.path.join(gen_dir, "theme-meta.json")
    palette_path = os.path.join(gen_dir, "palette.json")
    app_palette_path = os.path.join(gen_dir, "app-palette.json")
    colors_path = os.path.join(gen_dir, "colors.json")

    meta = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
        except Exception as e:
            print(f"[obsidian_themegen] Warning reading theme-meta.json: {e}", file=sys.stderr)

    palette_data = {}
    if os.path.exists(palette_path):
        try:
            with open(palette_path, "r") as f:
                palette_data = json.load(f)
        except Exception as e:
            print(f"[obsidian_themegen] Warning reading palette.json: {e}", file=sys.stderr)

    app_palette_data = {}
    if os.path.exists(app_palette_path):
        try:
            with open(app_palette_path, "r") as f:
                app_palette_data = json.load(f)
        except Exception:
            pass

    colors_data = {}
    if os.path.exists(colors_path):
        try:
            with open(colors_path, "r") as f:
                colors_data = json.load(f)
        except Exception:
            pass

    source = meta.get("source", "image")
    scheme_name = meta.get("scheme", "scheme-tonal-spot")
    mode = meta.get("mode", "dark")
    soften = meta.get("soften", True)
    is_preset = (source == "preset" or scheme_name == "preset")

    # Resolve seed color: metadata > palette > colors.json > fallback
    seed_color = meta.get("seed_color") or ""
    if not seed_color:
        seed_color = palette_data.get("primary") or colors_data.get("m3primary") or "#05B9F9"
    seed_hex = seed_color.lstrip("#")
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", seed_hex):
        seed_hex = "05B9F9"

    argb = 0xFF000000 | int(seed_hex, 16)
    hct = Hct.from_int(argb)
    SchemeClass = load_scheme_class(scheme_name)

    def gen_palette(dark):
        s = SchemeClass(hct, dark, 0.0)
        pal = {}
        for c in vars(MaterialDynamicColors).keys():
            cn = getattr(MaterialDynamicColors, c)
            if hasattr(cn, "get_hct"):
                g = cn.get_hct(s)
                if soften and scheme_name not in ["scheme-tonal-spot", "scheme-neutral", "scheme-monochrome"]:
                    g = Hct.from_hct(g.hue, g.chroma * 0.60, g.tone)
                pal[c] = rgba_to_hex(g.to_rgba())
        if dark:
            pal["success"] = "#B5CCBA"
            pal["onSuccess"] = "#213528"
            pal["successContainer"] = "#374B3E"
            pal["onSuccessContainer"] = "#D1E9D6"
        else:
            pal["success"] = "#4F6354"
            pal["onSuccess"] = "#FFFFFF"
            pal["successContainer"] = "#D1E8D5"
            pal["onSuccessContainer"] = "#0C1F13"
        return pal

    dp = gen_palette(True)
    lp = gen_palette(False)

    # For the active mode, overlay pre-computed tokens from palette.json / app-palette.json
    active_pal = dp if mode == "dark" else lp
    for src in (palette_data, app_palette_data):
        for k, v in src.items():
            if isinstance(v, str) and v.startswith("#"):
                active_pal[k] = v
                camel = snake_to_camel(k)
                snake = camel_to_snake(k)
                active_pal[camel] = v
                active_pal[snake] = v

    if is_preset and mode == "dark":
        for k, v in palette_data.items():
            if isinstance(v, str) and v.startswith("#"):
                dp[k] = v
                dp[camel_to_snake(k)] = v

    class _Hex:
        __slots__ = ("hex", "hex_stripped", "rgb")
        def __init__(self, hexval):
            self.hex = hexval
            self.hex_stripped = hexval.lstrip("#")
            h = self.hex_stripped
            if len(h) >= 6:
                self.rgb = f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
            else:
                self.rgb = "0, 0, 0"

    class _Token:
        __slots__ = ("dark", "light", "default")
        def __init__(self, dk, lt, is_dark_mode=True):
            self.dark = _Hex(dk)
            self.light = _Hex(lt)
            self.default = self.dark if is_dark_mode else self.light

    is_dark_mode = (mode == "dark")
    colors_ns = {}
    all_toks = set(dp.keys()) | set(lp.keys())
    for tok in all_toks:
        dk = dp.get(tok, "#000000")
        lt = lp.get(tok, "#000000")
        t = _Token(dk, lt, is_dark_mode)
        colors_ns[tok] = t
        snake = camel_to_snake(tok)
        if snake != tok:
            colors_ns[snake] = t
        camel = snake_to_camel(tok)
        if camel != tok:
            colors_ns[camel] = t

    tpl_path = resolve_template_path()
    if not tpl_path:
        print("[obsidian_themegen] Notice: inir-theme.css template not found, skipping", file=sys.stderr)
        return 0

    with open(tpl_path, "r") as f:
        content = f.read()

    _VAR_RE = re.compile(r"\{\{\s*(.*?)\s*\}\}")

    def _resolve(match):
        expr = match.group(1)
        parts = expr.split(".")
        if len(parts) == 4 and parts[0] == "colors":
            _, token, mode_str, prop = parts
            tok_obj = colors_ns.get(token)
            if not tok_obj:
                return match.group(0)
            mode_obj = getattr(tok_obj, mode_str, None)
            if not mode_obj:
                return match.group(0)
            return getattr(mode_obj, prop, match.group(0))
        return match.group(0)

    rendered = _VAR_RE.sub(_resolve, content)

    if not vaults:
        # If no vaults detected, still exit cleanly
        return 0

    for v in vaults:
        out_path = os.path.join(v, ".obsidian/snippets/inir-theme.css")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(rendered)
        print(f"✓ Generated Obsidian theme snippet ({scheme_name}, {mode}): {out_path}")

        app_json_path = os.path.join(v, ".obsidian/appearance.json")
        try:
            if os.path.exists(app_json_path):
                with open(app_json_path, "r") as af:
                    app_data = json.load(af)
            else:
                app_data = {}
            snippets = app_data.get("enabledCssSnippets", [])
            if "inir-theme" not in snippets:
                snippets.append("inir-theme")
                app_data["enabledCssSnippets"] = snippets
                with open(app_json_path, "w") as af:
                    json.dump(app_data, af, indent=2)
                print(f"✓ Enabled inir-theme snippet in {app_json_path}")
        except Exception as e:
            print(f"[obsidian_themegen] Notice: Could not auto-enable snippet in {app_json_path}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
