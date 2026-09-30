# SSH and access

## Contents

- [The safe change sequence](#the-safe-change-sequence)
- [sshd directives that matter](#sshd-directives-that-matter)
- [Accounts and keys](#accounts-and-keys)
- [sudo rule design](#sudo-rule-design)
- [Verifying a fleet change](#verifying-a-fleet-change)
- [Lockout recovery](#lockout-recovery)

## The safe change sequence

This is the class of change most likely to lock everyone out, so the sequence is fixed.

1. **Prove the second way in.** An already-open second session is the weakest form; a tested console or out-of-band path is the reliable one. Know which you have.
2. **Back up the effective and the file state.** Use fresh, protected backup paths for this change; the paths below assume they do not already exist.

   ```bash
   sudo cp -a /etc/ssh /root/ssh.bak
   sudo sh -c 'umask 077; sshd -T > /root/sshd.effective.before'
   ```

   Inspect `Include` directives and back up any files you will edit outside `/etc/ssh` as well. Inventory file names and contents before editing, including drop-ins; use a fresh protected backup path rather than overwriting a prior copy. Record the actual file paths and a rollback command before editing; the `sshd -T` output is evidence, not a restorable file.
3. **Edit, then validate before reloading.** `sudo sshd -t` parses the config and exits non-zero on a syntax error. Record the distro's SSH service name (`ssh` or `sshd`) and use it in the reload. A daemon that reloads a broken config can drop every connection.
4. **Reload, do not restart, where reload is supported.** `sudo systemctl reload` with the recorded SSH service name keeps existing sessions; a restart can close them.
5. **Open a new connection** from a different terminal using the intended user, source and authentication method. If it fails, use the still-open session to restore the exact changed files from their backups (for example `sudo cp -a /root/ssh.bak/. /etc/ssh/` and the recorded external includes), remove only newly introduced files identified against the before inventory, then run `sudo sshd -t` and reload the recorded distro SSH service; stop and use the tested console if validation fails. Restore changed sudoers files and drop-ins from their saved copies, remove newly introduced sudo drop-ins, and run `sudo visudo -c` before relying on sudo again.
6. **Only then close the old session.**

The same shape applies to `sudoers`, with `visudo -c` in place of `sshd -t` and `visudo` as the editor.

## sshd directives that matter

Read the effective config, not the file: includes and defaults mean the file does not show what the daemon uses. The following command shows the global context; use `-C` with the actual connection context below to check `Match` rules.

```bash
sudo sshd -T | sort
```

| Directive | Sensible value | What it costs |
| --- | --- | --- |
| `PermitRootLogin` | `prohibit-password` or `no` | An emergency root path must exist elsewhere |
| `PasswordAuthentication` | `no` once keys work | A lost key needs the console |
| `KbdInteractiveAuthentication` | `no` | Same |
| `PubkeyAuthentication` | `yes` | — |
| `AllowUsers` / `AllowGroups` | the named set | A new user is locked out until added |
| `MaxAuthTries` | `3` to `6` | Too low and a flaky agent locks people out |
| `LoginGraceTime` | `30` to `60` | Too low and slow MFA fails |
| `ClientAliveInterval` / `ClientAliveCountMax` | a deliberate peer-liveness probe policy | An unresponsive client may be disconnected; these settings do not measure human inactivity |
| `X11Forwarding` | `no` on a server | Breaks X forwarding if anyone relied on it |
| `AllowAgentForwarding` | `no` unless needed | Breaks the hop-through workflow |
| `UsePAM` | `yes` | Disabling it breaks account and session modules |
| `MaxSessions` | bounded | — |

`ssh-keyscan` and host key verification are a separate concern: pinning host keys in `known_hosts` stops a machine-in-the-middle on first connection, and rotating a host key is a planned change with its own comms.

## Accounts and keys

- Audit root-equivalence, not just the root account: `awk -F: '$3==0 {print $1}' /etc/passwd`.
- Lock accounts that cannot log in rather than deleting them, so file ownership survives: `usermod -L -s /usr/sbin/nologin <user>`.
- Service accounts get a locked password and a non-login shell.
- Enforce key type and size. Remove `ssh-dss` and short RSA keys; prefer Ed25519. A key is standing access, so it rotates like a credential.
- `authorized_keys` deserves the same review as `sudoers`: an unused key from a departed engineer is the access that outlives the offboarding.
- Consider a certificate authority for a fleet instead of distributing keys; it makes expiry and revocation possible.

## sudo rule design

- Prefer group rules (`%ops ALL=(ALL) ALL`) over per-user lists, so the rule tracks the group.
- `NOPASSWD` is a deliberate exception for automation, not a convenience for humans. Name why in the file.
- Constrain commands where the role allows it (`/usr/bin/systemctl restart nginx`), but know that a command with an escape — an editor, a shell, a `*` glob — is equivalent to full root.
- Never edit `sudoers` with a plain editor. A syntax error disables `sudo` for everyone; `visudo` refuses to save one.
- Log and review `sudo`: separate `sudo` logs to the off-host pipeline so privilege use is visible.

## Verifying a fleet change

Change one canary, then verify before the rest:

```bash
set -Eeuo pipefail
# On the canary, from a new session:
effective=$(ssh -n -o BatchMode=yes canary 'sudo -n sshd -T -C user=deploy,host=client.example,addr=192.0.2.10')
printf '%s\n' "$effective" | grep -E 'passwordauthentication|permitrootlogin'
# Confirm the fleet still matches the intended state after rollout:
while IFS= read -r h; do
  effective=$(ssh -n -o BatchMode=yes "$h" 'sudo -n sshd -T -C user=deploy,host=client.example,addr=192.0.2.10') || exit 1
  printf '%s\n' "$effective" | sha256sum
done < hosts.txt
```

A fleet rollout gets a change window, an order, and an abort condition. The canary result is evidence, not permission to change everything at once.
Replace the example `-C` user, client hostname and client address with each actual tested connection context; supply `laddr` and `lport` too when `Match LocalAddress` or `Match LocalPort` applies. `Match` directives can yield different effective settings for other users, sources or listening endpoints. Test a real new login as that user from that source after every reload. Save the raw output as well when its values matter: a hash alone cannot explain drift.

## Lockout recovery

If SSH is lost, the recovery depends on what you preserved.

- **Console or out-of-band** (IPMI, cloud serial, hypervisor console): log in, restore the backup, reload.
- **A still-open session**: restore from the backup and reload before it closes.
- **Neither**: single-user mode or a rescue image, which needs physical or console access and a reboot — and is why the second way in is gate one, not a nice-to-have.

Recovery is faster when the backup is on the host and the restore command is written down. Reconstructing the original config under pressure is where a short outage becomes a long one.
