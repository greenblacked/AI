# Mandatory access control playbook

## Contents

- SELinux workflow
- Labelling a custom path
- Booleans
- Scoped permissive mode
- AppArmor workflow

## SELinux workflow

```bash
getenforce
ls -Z /path/to/file
ausearch -m avc,user_avc,selinux_err -ts recent
ausearch -m avc -ts recent | audit2why
```

`ls -Z` shows the file's label; the AVC record shows the source domain, target type and denied permission. `audit2why` says whether the cause is a wrong label, a missing boolean or missing policy. If auditd is not running, the denials are in the kernel log or the journal (`journalctl -k | grep AVC`). A file created in one place and moved with `mv` keeps its old label; copying makes a new one with the destination's default.

Restore the default label for the path:

```bash
restorecon -Rv /path
```

## Labelling a custom path

When data lives outside the standard locations, teach the policy about it once, so a relabel does not undo the work:

```bash
semanage fcontext -a -t httpd_sys_rw_content_t '/srv/site(/.*)?'
restorecon -Rv /srv/site
```

Pick the type from the service's own documentation (the man page `SERVICE_selinux` where installed). Using a broad type such as `public_content_rw_t` to make an error disappear is a policy decision to make deliberately.

## Booleans

```bash
getsebool -a | grep httpd
setsebool -P httpd_can_network_connect on
```

`-P` makes it persistent. Use a boolean when `audit2why` names one; it is the supported switch.

## Scoped permissive mode

To prove SELinux is the cause without disabling it everywhere:

```bash
semanage permissive -a httpd_t
# reproduce, then read the logged would-be denials
semanage permissive -d httpd_t
```

Permissive records denials without enforcing them. Use `audit2allow` to draft a module only after labels and booleans are ruled out, review the generated rules by reading them, and treat the module as policy change needing approval.

## AppArmor workflow

```bash
aa-status
journalctl -k | grep 'apparmor="DENIED"'
aa-complain /etc/apparmor.d/PROFILE
# exercise the feature
aa-logprof
aa-enforce /etc/apparmor.d/PROFILE
```

The log line names the profile, the operation, the requested path and the permissions. Prefer adding a rule for the exact path and mode through a local override under `/etc/apparmor.d/local/` over editing the packaged profile. Reload with `apparmor_parser -r PROFILE`.
