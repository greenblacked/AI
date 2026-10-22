# Clean rooms

Read this when building the environment for a tutorial run. A clean room has what the
page's prerequisites list and nothing else; every extra tool, credential or cache is a
step the reader does not have and the run will not notice is missing.

## Contents

- [Choosing the room](#choosing-the-room)
- [Recipes](#recipes)
- [Accounts, email and the network](#accounts-email-and-the-network)
- [Contamination checklist](#contamination-checklist)

## Choosing the room

| Tutorial runs on | Room | Why |
| --- | --- | --- |
| Linux command line only | A new container from a minimal image | Cheap, disposable, inherits nothing from the host by default |
| Command line that itself uses Docker or systemd | A new Linux VM | Docker inside a container needs privileged nesting that a reader never has, and systemd is usually absent from container images |
| macOS | A new macOS VM, or a new local user account at minimum | A new user still shares system-wide installs such as Homebrew under `/opt/homebrew`; a VM does not |
| Windows | Windows Sandbox, or a new VM | Sandbox starts clean and discards everything when closed |
| A web console or sign-up flow | A new browser profile and a new account | Cookies, saved sessions and extensions all change what the reader sees |

Test at the minimum version the prerequisites state, not the latest. "Python 3.10 or later"
is a claim about 3.10, and the newest interpreter is where that claim is least tested.

## Recipes

Linux container, thrown away on exit, with the digest recorded for the run log:

```bash
docker pull ubuntu:24.04
docker image inspect --format '{{index .RepoDigests 0}}' ubuntu:24.04
docker run --rm -it --name tutorial-run ubuntu:24.04 bash
```

When the page states a language runtime as a prerequisite, start from that runtime's
official minimal image at the stated minimum version rather than installing it yourself,
so the room matches the reader's starting point and not your installation habits.

Linux VM with Multipass, for tutorials that need a real init system or Docker:

```bash
multipass launch 24.04 --name tutorial-run
multipass shell tutorial-run
# after the run
multipass delete --purge tutorial-run
```

Browser, a profile that exists for one run only:

```bash
google-chrome --user-data-dir="$(mktemp -d)"
firefox -no-remote -profile "$(mktemp -d)"
```

A private window is the minimum when a new profile is not possible. A new profile is
better because it also drops extensions, saved passwords and autofill, any of which can
complete a form field the page forgot to mention.

## Accounts, email and the network

- **A new account per run**, created by following the page. Reusing the previous run's
  account skips sign-up, email confirmation and every first-run screen, which are the
  steps most likely to have changed.
- **A new email address per run.** Some products reject or merge plus-addressed variants,
  so a mailbox per run, or a disposable domain the team controls, gives a cleaner signal.
- **Default quotas and settings.** New cloud projects often start with lower quotas and
  with service APIs not yet enabled; a staff project hides both. If the reader needs to
  enable something, the page has to say so.
- **The public network path.** Run off the corporate VPN and outside any office IP
  allowlist, with no internal package mirror or proxy configured. A mirror that already
  has the package hides a public registry that does not, and an allowlisted IP hides a
  firewall rule the reader will hit.

## Contamination checklist

Clear each line before starting the clock. One unchecked line is enough to make a broken
step pass.

- [ ] Environment created for this run, not reused from a previous one
- [ ] No host home directory, SSH agent socket or cloud credential directory mounted
- [ ] No environment file or exported variables passed in from the host
- [ ] No package manager configuration pointing at an internal registry or mirror
- [ ] No tool installed beyond the page's stated prerequisites
- [ ] Runtime at the minimum version the page states
- [ ] Account created fresh, with no staff role, feature flag or raised quota
- [ ] Network path matches a member of the public: no VPN, allowlist or proxy
- [ ] Browser profile new, or a private window at minimum
- [ ] Image digest, platform and product version recorded in the run log
