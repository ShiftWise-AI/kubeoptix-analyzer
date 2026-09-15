FROM registry.access.redhat.com/ubi10:1785332448

USER 0

WORKDIR /app

ENV LOG_DIR=/app/logs/ \
    DATA_DIR=/app/data/ \
    VENV_DIR=/app/.venv \
    REPORT_DIR=/app/report \
    HOME=/tmp \
    KUBECONFIG=/tmp/.kube/config \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KUBEOPTIX_API_HOST=0.0.0.0 \
    KUBEOPTIX_API_PORT=8000 \
    MPLCONFIGDIR=/tmp/matplotlib

ENV PATH=/app/.venv/bin:$PATH

RUN dnf install -y \
    python3 \
    python3-pip \
    graphviz \
    && dnf update -y \
    && dnf clean all \
    && useradd -m -s /bin/bash kubeoptix \
    && mkdir -p $LOG_DIR \
    && mkdir -p $DATA_DIR \
    && chown -R kubeoptix:kubeoptix /app \
    && chmod -R 777 /tmp \
    && chmod -R u+rwX /app

USER kubeoptix

COPY run-ocp.sh .
COPY api.py .
COPY requirements.txt .
COPY --chown=kubeoptix:kubeoptix agent/ /app/agent/

RUN find /app/agent -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name ".cache" \) -prune -exec rm -rf {} + \
    && find /app/agent -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*~" -o -name ".DS_Store" \) -delete

RUN python3 -m venv $VENV_DIR \
    && $VENV_DIR/bin/pip install --upgrade pip \
    && $VENV_DIR/bin/pip install --no-cache-dir "pygraphviz==2.0.1" \
    && $VENV_DIR/bin/pip install --no-cache-dir --no-deps "KubeDiagrams==0.8.0" \
    && $VENV_DIR/bin/pip install --no-cache-dir diagrams graphviz2drawio \
    && $VENV_DIR/bin/pip install --no-cache-dir -r requirements.txt \
    && $VENV_DIR/bin/kube-diagrams --help >/dev/null \
    && dot -V >/dev/null

EXPOSE 8000

CMD ["python", "api.py"]



