#!/usr/bin/env bash
# Runs inir-washi (scripts/colors/washi), building it first when its sources are newer than the binary.
# Usage: washi.sh --request '<json>' --out <file>  |  washi.sh --default
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
bin_dir="${XDG_STATE_HOME:-$HOME/.local/state}/quickshell/user/generated/bin"
bin="$bin_dir/inir-washi"

stale() {
  [[ -x "$bin" ]] || return 0
  local src
  for src in "$here"/washi/*.go "$root/go.mod"; do
    [[ "$src" == *_test.go ]] && continue
    [[ "$src" -nt "$bin" ]] && return 0
  done
  return 1
}

if stale; then
  go_bin="$(command -v go || true)"
  if [[ -z "$go_bin" ]]; then
    # `go` is often missing from a daemon's PATH (systemd user services do not
    # run a login shell), while a Go toolchain is still installed through Nix,
    # Homebrew or per-user profiles. Look in the well-known locations before
    # giving up: without it, iRiS stays wedged on the bundled fallback palette
    # forever.
    for candidate in \
      "$HOME/go/bin/go" \
      "$HOME/.local/bin/go" \
      /usr/local/go/bin/go \
      /usr/lib/go/bin/go \
      /usr/bin/go \
      /opt/homebrew/bin/go \
      "$HOME/.nix-profile/bin/go" \
      "/run/current-system/sw/bin/go"; do
      if [[ -x "$candidate" ]]; then
        go_bin="$candidate"
        break
      fi
    done
    # Nix: the user may have Go through a profile that is not on the service's
    # PATH; resolve the profile generation's store path directly.
    if [[ -z "$go_bin" ]]; then
      for profile in "$HOME"/.local/state/nix/profiles/profile/bin/go \
        /nix/var/nix/profiles/default/bin/go \
        /nix/var/nix/profiles/per-user/*/profile/bin/go; do
        if [[ -x "$profile" ]]; then
          go_bin="$profile"
          break
        fi
      done
    fi
    # Last resort on Nix: any Go toolchain already in the store, newest first.
    if [[ -z "$go_bin" ]] && [[ -d "/nix/store" ]]; then
      while IFS= read -r store_go; do
        if [[ -x "$store_go" ]]; then
          go_bin="$store_go"
          break
        fi
      done < <(find /nix/store -maxdepth 4 -path '*-go-*/bin/go' -type f 2>/dev/null | sort -r)
    fi
  fi
  if [[ -z "$go_bin" ]]; then
    [[ -x "$bin" ]] || { echo "washi: Go is not installed; iRiS keeps its default palette" >&2; exit 3; }
  else
    mkdir -p "$bin_dir"
    tmp="$bin_dir/.inir-washi.$$"
    if (cd "$root" && "$go_bin" build -trimpath -o "$tmp" ./scripts/colors/washi) >&2; then
      mv -f "$tmp" "$bin"
    else
      rm -f "$tmp"
      [[ -x "$bin" ]] || exit 4
    fi
  fi
fi

exec "$bin" "$@"
