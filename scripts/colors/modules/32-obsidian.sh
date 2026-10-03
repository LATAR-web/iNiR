#!/usr/bin/env bash
set -euo pipefail
# Obsidian theming module.
#
# Generates and deploys the Material You adaptive CSS snippet into all discovered
# Obsidian vaults, auto-enabling it in appearance.json.
#
# Called from: scripts/colors/applycolor.sh (color pipeline)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/lib/module-runtime.sh"
COLOR_MODULE_ID="obsidian"

THEMEGEN_SCRIPT="$SCRIPT_DIR/obsidian_themegen.py"

obsidian_installed() {
  command -v obsidian >/dev/null 2>&1 && return 0
  command -v md.obsidian.Obsidian >/dev/null 2>&1 && return 0
  [[ -d "$XDG_CONFIG_HOME/obsidian" ]] && return 0
  [[ -d "$HOME/.var/app/md.obsidian.Obsidian/config/obsidian" ]] && return 0
  [[ -d "$HOME/Documentos/Obsidiana" || -d "$HOME/Documents/Obsidian" ]] && return 0
  return 1
}

apply_obsidian_theme() {
  [[ -f "$THEMEGEN_SCRIPT" ]] || return 0
  obsidian_installed || return 0

  local enable_obsidian
  enable_obsidian=$(config_bool '.appearance.wallpaperTheming.enableObsidian' true)

  local python_cmd
  python_cmd="$(venv_python)"

  if [[ "$enable_obsidian" != 'true' ]]; then
    "$python_cmd" "$THEMEGEN_SCRIPT" --strip >> "$STATE_DIR/user/generated/code_editor_themes.log" 2>&1 || true
    return 0
  fi

  "$python_cmd" "$THEMEGEN_SCRIPT" >> "$STATE_DIR/user/generated/code_editor_themes.log" 2>&1 || true
}

main() {
  apply_obsidian_theme
}

main "$@"
