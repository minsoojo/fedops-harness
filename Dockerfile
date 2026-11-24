FROM node:22-bookworm-slim AS cli
RUN --mount=type=secret,id=build_ca if [ -f /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi; \
    npm install --prefix /opt/cli @anthropic-ai/claude-code@2.1.330 \
    && cp -L /opt/cli/node_modules/.bin/claude /tmp/claude \
    && /tmp/claude --version
FROM python:3.12-slim-bookworm
RUN mkdir -p /sandbox && chmod 1777 /sandbox
COPY --chmod=644 evidence/aggregation.py evidence/LICENSE /opt/fedops/evidence/
ADD evidence/repository-source.tar.gz /opt/fedops/repository/
RUN chmod -R a+rX,a-w /opt/fedops/repository
COPY --chmod=644 check.py worker.py stream_loop.py /opt/fedops/
RUN chmod 755 /opt/fedops /opt/fedops/evidence
WORKDIR /sandbox
COPY --from=cli --chmod=755 /tmp/claude /usr/local/bin/claude
CMD ["/bin/bash"]
