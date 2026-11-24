ARG BASE
FROM ${BASE}
COPY --chmod=644 codex_ask.py codex_edit.py check.py /opt/fedops/
COPY --chmod=644 evidence/aggregation.py /opt/fedops/evidence/
RUN chmod 755 /opt/fedops/evidence
