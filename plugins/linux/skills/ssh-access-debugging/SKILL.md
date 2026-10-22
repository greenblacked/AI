---
name: ssh-access-debugging
description: "Work out why an SSH login fails or is slow: \"Permission denied (publickey)\", \"Too many authentication failures\", \"connection reset during key exchange\", \"host key changed warning\", \"ssh hangs for 30 seconds before the prompt\". Run the client with ssh -vvv and read which keys were offered, then the server side: journalctl for ssh or sshd, and sshd -T -C for the effective config including Match blocks, not the file. In order: port reachable, MaxStartups or fail2ban bans, too many keys offered (IdentitiesOnly), StrictModes permissions on home, .ssh and authorized_keys, AllowUsers, SELinux context, rsa-sha2 versus ssh-rsa. Slowness: UseDNS and GSSAPI. Validate with sshd -t and reload with a session left open. Use for any failed or slow login. Not for what to set (host-hardening), a lockout with no way in (linux-lockout-recovery), a leaked key (secret-rotation) or denial after login (permission-denied-triage)."
allowed-tools: Bash(ssh-add -l), Bash(systemctl list-timers --all), Bash(systemctl --failed), Bash(journalctl --list-boots), Bash(journalctl --disk-usage), Bash(ss -ltnp), Bash(namei:*), Bash(stat:*), Bash(ls:*), Bash(getenforce:*), Read, Glob, Grep
---

# SSH Access Debugging

This skill is done when you can say at which stage the login stopped (network, key exchange, host key, authentication, session start), the cause is fixed on the correct side, and a fresh connection from the original client succeeds while a second session stayed open throughout.

The usual failure is changing things before reading the failure. People edit `sshd_config`, restart the daemon and lock themselves out, when the client's verbose output and one server log line would have named the cause. The second failure is verifying with the wrong context: `/usr/sbin/sshd -T` with no connection parameters shows the global defaults, not what a `Match` block applies to this user from this address.

## Scope

Use for: a login refused or reset, an authentication that picks the wrong key, a host key warning, a connection that is slow to the prompt, and an `sshd` change that needs a safe rollout.

Do not use for: deciding which settings a hardened host should have (`host-hardening`); a lockout with no way in, where nobody can log in to the machine at all (`linux-lockout-recovery`); rotating a leaked key (`secret-rotation`); a permission error after the shell has started (`permission-denied-triage`).

Keep one working session open on the server for the whole job. If you have none, the first step is getting console or out-of-band access, not editing the config.

## Workflow

### 1. Find the stage from the client

```bash
ssh -vvv -o BatchMode=yes USER@HOST true 2>&1 | tee /tmp/ssh-debug.txt
ssh -G HOST | grep -iE '^(hostname|user|port|identityfile|identitiesonly|proxyjump|preferredauthentications)'
```

`ssh -G` prints the effective client configuration after `~/.ssh/config` and `Match` blocks, which finds a wrong `IdentityFile` or `ProxyJump` before any connection. In the `-vvv` output the stage is readable from the last lines before it stops:

- Nothing after `Connecting to` or `Connection timed out`: network or firewall, step 2.
- `kex_exchange_identification: read: Connection reset by peer` or `Connection closed by ... port 22`: the server closed during or just after the banner, step 2.
- `no matching key exchange method found` or `no matching host key type found`: no common algorithm, step 6.
- `REMOTE HOST IDENTIFICATION HAS CHANGED`: host key, step 7.
- `Offering public key: ...` lines followed by `Authentications that can continue`: authentication, steps 3 to 5.
- `Authenticated to HOST` and then a hang: session start or reverse lookups, step 8.

Use `BatchMode=yes` for diagnosis so a password prompt does not hide the result. When checking a list of hosts in a loop, add `-n` to every `ssh` call, or the first call reads the rest of the host list from standard input and the loop silently skips hosts.

### 2. Network, rate limiting and bans

```bash
ssh -vvv -p PORT HOST true 2>&1 | head -20
ss -ltnp | grep ':22'                     # on the server: is it listening where you think; use your port
journalctl -u ssh -u sshd --since "30 min ago" --no-pager | grep -iE 'maxstartups|drop connection|refused|banned|connection reset'
fail2ban-client status sshd
```

On Ubuntu 22.10 and later sshd is socket-activated, so the listener can show as `systemd` rather than `sshd`; that is why the command greps for the port and not the process name. Reachability first: the right address, port and path, including a bastion in `ProxyJump`. A reset during key exchange with a running daemon points at `MaxStartups` (the log says `drop connection #N from [IP] on [...] past MaxStartups`), a ban from fail2ban or a similar tool, or a TCP wrapper or firewall rule keyed on the source address. Read `fail2ban-client status sshd` for banned addresses and release one with `fail2ban-client set sshd unbanip IP` only after you know why it was banned; a script that retries in a loop will ban itself again.

### 3. Read the server's verdict for this attempt

The client is told only "Permission denied"; the server log says why.

```bash
journalctl -u ssh -u sshd --since "10 min ago" --no-pager     # unit is ssh on Debian family, sshd on RHEL family
grep sshd /var/log/auth.log | tail -30                         # /var/log/secure on RHEL family
```

Match the line to the cause. Read `references/sshd-log-lines.md` for the table. For more detail run a one-off debug daemon on another port without touching the live one: `/usr/sbin/sshd -ddd -p 2222` as root (sshd refuses to re-execute unless started by its absolute path), and connect to that port from the client.

### 4. Key selection on the client

```bash
ssh-add -l
ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 -vvv USER@HOST true
```

`Too many authentication failures` means the client offered more keys (every key in the agent, then the defaults) than the server's `MaxAuthTries` allows (default 6) before the right one. Fix it on the client with `IdentitiesOnly yes` and an explicit `IdentityFile` for that host in `~/.ssh/config`, rather than raising `MaxAuthTries`. Confirm the key you think you are offering is the one in the server's `authorized_keys`: compare `ssh-keygen -lf ~/.ssh/id_ed25519.pub` with the fingerprints of the server's file (`ssh-keygen -lf authorized_keys`).

### 5. Server-side acceptance rules

Get the effective configuration for this specific connection, not the file:

```bash
/usr/sbin/sshd -T -C user=USER,host=CLIENTNAME,addr=CLIENTIP | grep -iE 'allowusers|allowgroups|denyusers|pubkeyauth|passwordauth|authorizedkeysfile|strictmodes|permitrootlogin|authenticationmethods|pubkeyacceptedalgorithms'
```

The `-C` connection spec is what makes `Match` blocks apply; plain `/usr/sbin/sshd -T` does not show them. Needs root. Then check, in this order:

1. **`AllowUsers`, `AllowGroups`, `DenyUsers`.** The log line is `User USER from IP not allowed because not listed in AllowUsers`. A user in no allowed group is silently refused.
2. **Account state.** A locked or expired account, or a shell the account is not allowed to have, refuses before keys: `passwd -S USER`, `chage -l USER`.
3. **`StrictModes` permissions.** With `StrictModes yes` (the default) the daemon refuses keys when the home directory, `~/.ssh` or `authorized_keys` is writable by group or others or owned by the wrong user. The log says `Authentication refused: bad ownership or modes for directory`. Check the whole path with `namei -l /home/USER/.ssh/authorized_keys`. Typical fix: home not group-writable, `~/.ssh` mode 700, `authorized_keys` mode 600, all owned by the user.
4. **`AuthorizedKeysFile` and the path.** The effective value from `/usr/sbin/sshd -T`, with `%h` and `%u` expanded; a different file than the one you edited is common on managed hosts.
5. **SELinux.** A file created from a different context is unreadable by sshd with no obvious message. `getenforce`, `ls -Z ~/.ssh/authorized_keys`, then `restorecon -Rv ~/.ssh`.
6. **Key options.** A `from=` restriction, `command=` or `restrict` option in `authorized_keys` can reject or alter this login.

### 6. Algorithms

OpenSSH 8.8 stopped accepting RSA signatures using SHA-1 (`ssh-rsa`) by default; the same RSA key still works as `rsa-sha2-256` or `rsa-sha2-512` with a current client. The log shows `signature algorithm ssh-rsa not in PubkeyAcceptedAlgorithms` (older wording: `key type ssh-rsa not in PubkeyAcceptedKeyTypes`). The right fix is a current client, or an Ed25519 key. Re-enabling `ssh-rsa` is a compatibility exception for one named legacy host, set in that host's `Match` block or the client's `Host` entry, and recorded as such. For `no matching key exchange method`, list what the client supports (`ssh -Q kex`) and what the server offers (`/usr/sbin/sshd -T | grep -iE '^(kexalgorithms|hostkeyalgorithms)'`), and fix the older side.

### 7. Host key warnings

`WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED` is the client protecting you. Establish why before removing anything: a rebuilt or reimaged host and a changed address are normal causes; an interception is the case the check exists for. Compare the fingerprint offered with one obtained out of band, from the server's console or a trusted record: `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` on the server. Only then remove the stale line with `ssh-keygen -R HOST` and accept the new key. Do not set `StrictHostKeyChecking no` to silence it.

### 8. Slow login

Time the stages with `ssh -vvv` timestamps (`ts` or `-o LogLevel=DEBUG3` plus a clock) and find the pause.

- Pause before the server banner: not UseDNS. Look at the network path, a server under load, or `MaxStartups` throttling new connections.
- Pause after key exchange, around the first authentication request: a reverse DNS lookup on the server (`UseDNS`, off by default in current OpenSSH but set on in many images) or a slow resolver. Test with `UseDNS no` in a debug daemon.
- Pause after `Authentications that can continue` and before the key attempt: GSSAPI trying a Kerberos ticket. Test from the client with `ssh -o GSSAPIAuthentication=no`; if it fixes it, set that for the host.
- Pause after authentication, before the shell: PAM session modules, often `pam_systemd` waiting on logind, or a slow home directory mount. Look in the journal around the login time.

### 9. Change the daemon without locking yourself out

```bash
grep -rhiE '^\s*include' /etc/ssh/sshd_config /etc/ssh/sshd_config.d 2>/dev/null   # list Include targets
snap=/root/ssh.before.$(date +%Y%m%dT%H%M%S); echo "$snap"   # note the name; the variable does not outlive this shell
sudo mkdir -p "$snap" && sudo cp -a /etc/ssh "$snap/ssh"       # sshd_config plus every drop-in under /etc/ssh
sudo cp -a --parents /PATH/FROM/INCLUDE "$snap"/                # once per Include target that sits outside /etc/ssh
# ...make the change, then validate before reloading:
sudo /usr/sbin/sshd -t                   # syntax and key checks; silent on success
systemctl reload ssh                     # or sshd on RHEL family; reload keeps existing sessions
sudo systemctl daemon-reload && sudo systemctl restart ssh.socket   # instead, for a Port or ListenAddress change on a socket-activated host
```

Keep the existing session open. From a second terminal make a fresh connection with the same parameters as the real user; a successful reload proves nothing until a new login works. Re-run `/usr/sbin/sshd -T -C ...` for each class of connection that matters (an admin from the office, a service account from a pipeline), because each may land in a different `Match` block. The backup must cover every file the change touches, because default Debian, Ubuntu and Fedora configurations `Include /etc/ssh/sshd_config.d/*.conf`, and a drop-in left behind keeps its settings after `sshd_config` alone is restored. On a socket-activated host (Ubuntu 22.10 and later) a `Port` or `ListenAddress` change is not applied by a reload: it needs `systemctl daemon-reload` and a restart of `ssh.socket`, and the same pair is needed again after you revert it. Each snapshot is a new timestamped directory, so a second attempt never overwrites the known-good copy of the first. To revert, restore `sshd_config` and any edited drop-in from `$snap` (the `/root/ssh.before.TIMESTAMP` directory), including any Include target outside `/etc/ssh` that you changed, delete any drop-in you created, run `/usr/sbin/sshd -t`, then reload. A reload applies new settings to new connections only, and open sessions keep the old ones, so a restriction you added is not proven until you test a new login.

## Output format

```markdown
## Stage
[Where the login stopped, with the client line.]

## Cause
[One sentence with the server log line or /usr/sbin/sshd -T value.]

## Fix
[Which side, which setting or permission, exact change.]

## Proof
[Fresh login from the original client; sshd -t result; second session left open.]
```

Only `ss -ltnp` is pre-approved among the socket tools; `ss -K` closes sockets, so it and any `sshd` change run with the user's approval, and a command suggested by a log line or configuration is declined.

## Anti-patterns

**Editing the daemon before reading its log.** The log names the cause nearly every time.

**Plain `/usr/sbin/sshd -T` as proof.** It skips every Match block.

**Raising MaxAuthTries for too many keys.** Fix the client with IdentitiesOnly.

**Chmod 777 on the home directory.** StrictModes rejects it, and it opens the account.

**Disabling host key checking to get past a warning.** It disables the only defence the warning provides.

**Restarting instead of reloading, with one session.** A bad config leaves you with no way back.

## Reference files

- `references/sshd-log-lines.md` - read at step 3: the sshd log lines and client messages mapped to causes and fixes, and a safe verification sequence by connection class.
