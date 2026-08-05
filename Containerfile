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
    KUBEOPTIX_API_PORT=8080 \
    KUBEOPTIX_MODE=local

ENV PATH=/app/.venv/bin:$PATH

RUN dnf install -y \
    python3 \
    python3-pip \
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
    && $VENV_DIR/bin/pip install --no-cache-dir -r requirements.txt 

EXPOSE 8080

CMD ["python", "api.py"]



