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
2. **Back up the effective and the file state.**

   ```bash
   sudo cp -a /etc/ssh/sshd_config /root/sshd_config.bak
   sudo sshd -T > /root/sshd.effective.before
   ```

3. **Edit, then validate before reloading.** `sshd -t` parses the config and exits non-zero on a syntax error. A daemon that reloads a broken config can drop every connection.
4. **Reload, do not restart, where reload is supported.** `systemctl reload sshd` keeps existing sessions; a restart can close them.
5. **Open a new connection** from a different terminal. If it works, the change is good. If it does not, use the still-open old session to restore the backup and reload.
6. **Only then close the old session.**

The same shape applies to `sudoers`, with `visudo -c` in place of `sshd -t` and `visudo` as the editor.

## sshd directives that matter

Read the effective config, not the file: includes and defaults mean the file does not show what the daemon uses.

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
| `ClientAliveInterval` / `ClientAliveCountMax` | a defined idle timeout | Long-running sessions get cut |
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
# On the canary, from a new session:
ssh -o BatchMode=yes canary 'sudo sshd -T | grep -E "passwordauthentication|permitrootlogin"'
# Confirm the fleet still matches the intended state after rollout:
for h in $(cat hosts.txt); do ssh -o BatchMode=yes "$h" 'sudo sshd -T' | sha256sum; done
```

A fleet rollout gets a change window, an order, and an abort condition. The canary result is evidence, not permission to change everything at once.

## Lockout recovery

If SSH is lost, the recovery depends on what you preserved.

- **Console or out-of-band** (IPMI, cloud serial, hypervisor console): log in, restore the backup, reload.
- **A still-open session**: restore from the backup and reload before it closes.
- **Neither**: single-user mode or a rescue image, which needs physical or console access and a reboot — and is why the second way in is gate one, not a nice-to-have.

Recovery is faster when the backup is on the host and the restore command is written down. Reconstructing the original config under pressure is where a short outage becomes a long one.
