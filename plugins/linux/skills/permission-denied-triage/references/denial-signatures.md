# Denial signatures

## Contents

- Errno to layer
- Symptom to layer

## Errno to layer

| Error | Meaning | Look at |
| --- | --- | --- |
| EACCES, "Permission denied" | Access refused on mode, ACL or policy | namei, getfacl, then MAC |
| EPERM, "Operation not permitted" | Privileged operation refused | lsattr, capabilities, seccomp, chown by non-owner |
| EROFS, "Read-only file system" | Mounted read-only, or sandbox read-only | findmnt, ProtectSystem |
| ENOENT, "No such file or directory" | Not a permission problem, but a missing parent or interpreter | Path, shebang line |
| "bad interpreter" | The script's first line names a missing or noexec interpreter | head -1 of script, mount options |

## Symptom to layer

| Symptom | Likely layer |
| --- | --- |
| 777 file still denied | A parent directory lacks x for the identity |
| Works as root, not as service user | Mode or ownership; or groups not applied to the running process |
| Works from shell, fails in the unit | systemd sandbox, or a different user and group |
| Cannot execute from /tmp or a data mount | noexec mount option |
| Even root cannot delete or modify | Immutable or append-only attribute |
| Root works locally, denied on NFS | Root squash on the export |
| Denied only on a non-default path | SELinux label for that path |
| Denial appears in audit log as AVC | SELinux |
| Denial in kernel log as apparmor="DENIED" | AppArmor |
| Port below 1024 refused to a non-root service | CAP_NET_BIND_SERVICE missing |
