# sshd log lines and client messages

## Contents

- Server log lines and what they mean
- Client messages and what they mean
- Verifying by connection class
- Permissions checklist

## Server log lines and what they mean

| Log line (abridged) | Cause | Fix |
| --- | --- | --- |
| `Authentication refused: bad ownership or modes for directory /home/USER` | StrictModes: home writable by group or others, or owned by someone else | Remove group and other write on the home directory |
| `Authentication refused: bad ownership or modes for file .../authorized_keys` | Same, for the file | `chmod 600`, correct owner |
| `User USER from IP not allowed because not listed in AllowUsers` | AllowUsers excludes the user, or the pattern has a typo or an address part | Edit the allow list, validate with `sshd -T -C` |
| `User USER from IP not allowed because a group is listed in DenyGroups` | Group deny | Remove from the group or adjust the rule |
| `User USER not allowed because account is locked` | Locked account | Unlock deliberately; a password lock often also blocks key login on some PAM setups |
| `userauth_pubkey: key type ssh-rsa not in PubkeyAcceptedAlgorithms` | Client signs with SHA-1 RSA | Use a current client or an Ed25519 key |
| `Failed publickey for USER from IP ... ssh2: RSA SHA256:...` | The offered key is not in the file the daemon read | Compare fingerprints, check `AuthorizedKeysFile` |
| `Could not open authorized keys '...': Permission denied` | Mode, owner or SELinux context | `namei -l`, `ls -Z`, `restorecon -Rv` |
| `drop connection #N from [IP]:PORT on [IP]:22 past MaxStartups` | Unauthenticated connection limit reached | Find the source of the flood, tune `MaxStartups` if the load is legitimate |
| `error: maximum authentication attempts exceeded for USER` | Client tried too many keys or passwords | `IdentitiesOnly` on the client |
| `Connection closed by authenticating user USER IP port N [preauth]` | Client gave up (a missing key, a failed prompt, a timeout) | Read the client `-vvv` for the reason |
| `Unable to negotiate with IP port N: no matching key exchange method found` | Client and server share no key exchange algorithm | Update the older side |
| `Bad protocol version identification` | Something other than SSH connected, or a port scan | Check what connects to the port |
| `pam_unix(sshd:account): account expired` or `pam_access` denial | PAM account stack refuses | `chage -l USER`, `/etc/security/access.conf` |
| `fatal: Access denied for user USER by PAM account configuration` | PAM account stack | As above |

## Client messages and what they mean

| Message | Meaning |
| --- | --- |
| `Permission denied (publickey)` | The server accepted only keys and rejected all offered; the cause is on the server log |
| `Permission denied (publickey,password)` | Both methods were tried and failed |
| `Too many authentication failures` | More keys offered than `MaxAuthTries` allows |
| `Connection refused` | Nothing is listening, or a firewall rejects actively |
| `Connection timed out` | Packets are dropped, or the route or address is wrong |
| `kex_exchange_identification: Connection closed by remote host` | The server accepted the TCP connection and closed before the banner exchange; limits, bans or wrappers |
| `Host key verification failed` | The known_hosts entry does not match, or checking is strict and the host is unknown |
| `Bad owner or permissions on /home/USER/.ssh/config` | The client refuses a config file others can write |
| `Load key "...": invalid format` | A damaged or wrong-format private key, or a trailing-newline loss when copied |
| `Unable to negotiate with HOST: no matching host key type found. Their offer: ssh-rsa` | The server offers only an algorithm the client disabled |

## Verifying by connection class

Run `sshd -T` once per class of connection that matters, with the user, the source name and the source address that class really has, and compare the lines that decide the result.

```bash
sshd -T -C user=alice,host=office-gw,addr=203.0.113.10 | grep -iE '^(allowusers|passwordauthentication|pubkeyauthentication|authenticationmethods|permitrootlogin)'
sshd -T -C user=deploy,host=ci-runner,addr=198.51.100.7 | grep -iE '^(allowusers|passwordauthentication|pubkeyauthentication|authenticationmethods|forcecommand)'
```

The addresses above are documentation ranges; use the real ones. Then open a fresh connection for each class from a real client of that class. The static output says what the daemon will decide, and the live login says whether the path to it works; one without the other leaves a gap.

## Permissions checklist

```bash
namei -l /home/USER/.ssh/authorized_keys
stat -c '%U:%G %a %n' /home/USER /home/USER/.ssh /home/USER/.ssh/authorized_keys
```

- Every directory from `/` to the file is owned by root or the user and not writable by group or others (a group-writable parent such as a shared home trips StrictModes).
- `~/.ssh` is 700, `authorized_keys` is 600 (644 is accepted when it is not group or world writable, but 600 is the habit).
- The file ends with a newline, each key on one line with no wrapping introduced by a copy and paste.
- On SELinux hosts the file has the `ssh_home_t` type; `restorecon -Rv ~/.ssh` sets it from policy.
