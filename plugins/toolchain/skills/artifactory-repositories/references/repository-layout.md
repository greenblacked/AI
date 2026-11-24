# Repository layout and resolution

Read when designing or auditing the repositories of one package type, or when a client
resolves something it should not. Names, settings and REST paths differ between
versions and licence tiers; check the official docs for the pinned version and record
the version each claim was checked on.

## Contents

- A layout per package type
- Resolution order and the confusion check
- Permission targets
- Client configuration

## A layout per package type

For each package type keep this shape, named by lifecycle stage:

| Repository | Kind | Holds | Who deploys |
| --- | --- | --- | --- |
| `<type>-dev-local` | local | every CI build, snapshots | the build pipelines |
| `<type>-staging-local` | local | candidates promoted after tests | the promotion job only |
| `<type>-release-local` | local | released, immutable | the promotion job only |
| `<type>-public-remote` | remote | cache of the public registry | nobody (read through) |
| `<type>-dev` | virtual | dev-local, release-local, public-remote | nobody |
| `<type>-release` | virtual | release-local, public-remote | nobody |

Production builds resolve from the release virtual repository, so nothing unreleased
and internal can be pulled into a production build. Developer builds resolve from the
dev virtual repository. Whether one virtual repository can mix package types is
decided by the product, so keep one per type.

## Resolution order and the confusion check

A virtual repository checks local repositories before remote ones whatever order the
members are listed in, and for package types with version ranges it merges the members'
metadata so the highest version across them is offered. List order is therefore not the
control; the local repository's Priority Resolution setting and include or exclude
patterns on a member are, so read the members' own settings, not only the list. A remote repository caches whatever
upstream returns for a name, including a public package that shares a name with an
internal one.

To prove a name cannot resolve upstream:

1. List the virtual repository's members and their order from the configuration API.
2. Confirm the internal local repository has Priority Resolution set, or that the
   remote's exclude patterns cover the internal namespace.
3. Request the internal name through the virtual repository with the CI identity and
   note which member the response header or storage path names.
4. Request a name that exists only publicly and confirm it still resolves, so the
   exclusion is not hiding everything.
5. Search the remote repository's cache for any internal name; a hit means the
   exposure already happened and the cached artifact should be removed and the
   package reported to `dependency-triage`.

An internal namespace you do not own publicly is the weak point: register or reserve
the scope or group id upstream where the registry allows it.

## Permission targets

Create one permission target per repository set and role, and assign groups, not
individuals:

- build: deploy to dev-local; read on the dev virtual and remote repositories.
- promote: read dev-local and staging-local; deploy to staging-local and release-local.
- consume: read on the release virtual repository only.
- admin: delete and overwrite on release-local, held by a small group.

Check the action names the pinned version offers (the usual set is read, annotate,
deploy or cache, delete or overwrite, manage) and whether anonymous access is off.
Export the permission configuration and compare it to this table; a drift between the
two is an audit finding.

## Client configuration

A client points at one virtual repository URL per type, set in the tool's own config
(a settings file, an `.npmrc`, a `pip.conf`, a Gradle or Docker config) kept in the
repository without credentials. Credentials come from the CI variable store or the
developer's keychain through the tool's login command. Generate the config with the
CLI's build configuration commands where the pinned CLI version supports them, and
check the result in rather than relying on a developer's machine state.
