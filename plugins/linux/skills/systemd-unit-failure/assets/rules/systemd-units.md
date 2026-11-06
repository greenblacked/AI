---
paths:
  - "**/*.service"
  - "**/*.service.d/*.conf"
---

# Writing a systemd service unit

Diagnosing a unit that fails belongs to the `systemd-unit-failure` skill; this rule is only
the guard that loads when a unit file is open.

- Start the program with an absolute path in `ExecStart=`. A path with a slash that does not
  start with one (`./server`, `bin/run`) is refused by systemd, and the unit fails with
  status 203/EXEC before the program runs, so its own log stays empty.
- Put changes to a packaged unit in a drop-in (`systemctl edit UNIT`), never in the vendor
  file under `/usr/lib/systemd/system`, which the next package update overwrites.
- Pair `After=` with `Wants=` or `Requires=`: ordering alone starts nothing, and the
  dependency alone orders nothing.
- Give `Restart=` a `RestartSec=` of seconds. A zero pause turns a crash into a loop that ends
  in start-limit-hit.
- Prove the change with `systemd-analyze verify UNIT` and a stop/start, then check the boot
  order, because a manual restart passes in conditions a reboot does not.
