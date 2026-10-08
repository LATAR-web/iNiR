# ADR-0002: The "usable systemd user manager" predicate governs the port

Void can run systemd; an Arch box can lack a working user manager. Every
systemd-sensitive path in iNiR is therefore gated by a predicate, not by
`command -v systemctl` and not by distro name.

The predicate: the socket `$XDG_RUNTIME_DIR/systemd/private` exists and a
bounded probe of `systemctl --user` answers:
`timeout 3s systemctl --user show-environment`.

Paths it gates:

- install: `inir.service` unit vs `~/.config/service/inir/run`
- migrations 021/022
- `scripts/inir`: restart/kill/stop/status/logs
- runtime UI and environment operations that use `systemctl --user` or
  `systemd-run`
- distribution-test invariants

Without the socket, `systemctl --user` can block for 10-30 seconds, so the
socket check comes first and the probe is bounded.

Status: accepted and verified across runtime and maintenance paths. Future
systemd-sensitive work remains subject to this predicate.
