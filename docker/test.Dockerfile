# syntax=docker/dockerfile:1
#
# The test environment, built to the same pins CI installs. The base image is pinned by
# digest rather than tag: a tag is whatever the publisher moved it to this morning, and a
# test environment that changes underneath the suite is worse than no second environment.
#
# Versions arrive as build arguments from the Makefile, which reads them out of
# .github/workflows/ci.yml — the same single source of truth the rest of the repository
# uses. Nothing here restates a version.
FROM python:3.13-slim-bookworm@sha256:e32be0e55814a08977501ca863271d9bd02443710db8f2afaf8372e2c4508530

ARG PYTEST_VERSION
ARG PYTEST_XDIST_VERSION
ARG PYTEST_COV_VERSION
ARG COVERAGE_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/work/src \
    TMPDIR=/tmp \
    PYTEST_ADDOPTS="-p no:cacheprovider"

# Run as an unprivileged user: the suite executes shell from Markdown fences and builds
# the site, and neither needs to own root in the container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends make git curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 tester \
    && useradd --uid 1000 --gid 1000 --create-home tester

WORKDIR /work
COPY --chown=1000:1000 . /work/

# The copy sets file ownership but not the directory it lands in; git refuses a repository
# it sees as owned by another user.
RUN chown tester:tester /work

RUN python -m pip install --no-cache-dir \
    "pytest==${PYTEST_VERSION}" \
    "pytest-xdist==${PYTEST_XDIST_VERSION}" \
    "coverage==${COVERAGE_VERSION}" \
    "pytest-cov==${PYTEST_COV_VERSION}"

USER tester

# The same three commands a contributor runs before opening a pull request. `make coverage`
# is deliberately not here: it writes .coverage into the working tree, and the container
# runs read-only. Use the host target when the coverage table is what you want.
CMD ["make", "validate", "catalogue", "test"]
