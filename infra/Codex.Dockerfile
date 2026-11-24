FROM rust:1.99.1-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends clang cmake lld libcap-dev libasound2-dev protobuf-compiler && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY --from=codex . .
ARG CODEX_REV
RUN test -n "$CODEX_REV" && git config --global --add safe.directory /src && test "$(git rev-parse HEAD)" = "$CODEX_REV" && test -z "$(git status --porcelain --untracked-files=normal)"
RUN set -eu; target=x86_64-unknown-linux-gnu; profile=ptrcomp_sandbox_release; \
    version=$(python3 .github/scripts/rusty_v8_bazel.py resolved-v8-crate-version); \
    base="https://github.com/openai/codex/releases/download/rusty-v8-v${version}"; \
    manifest="rusty_v8_${profile}_${target}.sha256"; mkdir /v8; \
    cp third_party/v8/*_release_manifests.sha256 /v8/; cd /v8; \
    curl -fsSLO "$base/$manifest"; grep -hF "  $manifest" *_release_manifests.sha256 | sha256sum -c -; \
    for artifact in "librusty_v8_${profile}_${target}.a.gz" "src_binding_${profile}_${target}.rs"; do curl -fsSLO "$base/$artifact"; done; \
    sha256sum -c "$manifest"
# Use the pinned Rust bindings with the verified prebuilt V8 archive above.
# Cargo's default Git fetch would also clone Chromium's source submodules.
WORKDIR /src/codex-rs
RUN set -eu; rev=90a65f887a0c0f048f3784afbcb320b373c8a2e0; \
    mkdir /v8/crate; git init -q /v8/crate; git -C /v8/crate fetch -q --depth 1 https://github.com/openai-oss-forks/rusty_v8.git "$rev"; \
    git -C /v8/crate checkout -q "$rev"; \
    grep -F "v8 = { git = \"https://github.com/openai-oss-forks/rusty_v8.git\", rev = \"$rev\" }" Cargo.toml; \
    sed -i '/^v8 = { git = .*rusty_v8.git/c\v8 = { path = "/v8/crate" }' Cargo.toml; \
    sed -i '\|^source = "git+https://github.com/openai-oss-forks/rusty_v8.git|d' Cargo.lock
ENV CARGO_PROFILE_DEV_DEBUG=0 CARGO_INCREMENTAL=0 CARGO_BUILD_JOBS=3 \
    RUSTY_V8_ARCHIVE=/v8/librusty_v8_ptrcomp_sandbox_release_x86_64-unknown-linux-gnu.a.gz \
    RUSTY_V8_SRC_BINDING_PATH=/v8/src_binding_ptrcomp_sandbox_release_x86_64-unknown-linux-gnu.rs
RUN --mount=type=cache,target=/usr/local/cargo/git --mount=type=cache,target=/usr/local/cargo/registry --mount=type=cache,target=/src/codex-rs/target \
    STABLE_GIT_COMMIT="$CODEX_REV" cargo build --locked --bin codex-exec && install -s target/debug/codex-exec /usr/local/bin/fedops-codex
FROM python:3.12-slim-bookworm
ARG CODEX_REV
RUN mkdir -p /opt/fedops && echo "$CODEX_REV" > /opt/fedops/codex-revision
COPY --from=build /usr/local/bin/fedops-codex /usr/local/bin/fedops-codex
RUN mkdir -p /sandbox && chmod 1777 /sandbox
WORKDIR /sandbox
ADD evidence/repository-source.tar.gz /opt/fedops/repository/
COPY --chmod=644 codex_ask.py repository_mcp.py stream_loop.py /opt/fedops/
