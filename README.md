# kubeoptix-analyzer

`kubeoptix-analyzer` is an OpenShift and Kubernetes assessment tool that reads previously collected workload artifacts, inspects their configuration and runtime metadata, and produces a Markdown report with findings, risks, and suggested remediation actions.

The project is designed for artifact-based analysis rather than live cluster mutation. It expects pre-collected manifests, logs, and worker-node inventory to already exist in a structured directory before execution. The analyzer then reviews workloads, services, routes, ConfigMaps, operators, and observability data to identify configuration and reliability issues.

## Features

- Parses Kubernetes and OpenShift YAML manifests from collected artifacts.
- Evaluates workloads, services, routes, ConfigMaps, and operators for configuration risk.
- Reviews CPU and memory requests/limits, HPA signals, and node capacity.
- Identifies missing readiness/liveness probes, insecure routes, and common misconfigurations.
- Scans logs for error patterns and observability gaps.
- Produces a Markdown assessment report for a namespace or for all discovered namespaces.
- Runs as a CLI or through an HTTP API in a containerized OpenShift deployment.

## Requirements

- Python 3.9+
- Bash
- Helm 3 (for OpenShift deployment)
- OpenShift or Kubernetes cluster access for artifact collection and deployment
- A prepared artifact directory containing collected manifests, logs, and node data
- Optional: `oc` CLI for the Helm/OpenShift installation flow

## Technologies

- Python 3 for the analyzer logic and API
- OpenShift and Kubernetes manifest parsing
- Helm chart for deployment in OpenShift
- Containerfile/OCI image build for runtime packaging
- HTTP API using Python standard library (`http.server`)
- `.env`-based configuration for LLM and cursor integrations
- Git-based image builds and OpenShift `BuildConfig`/`ImageStream` resources

## Project Structure

```text
.
├── agent/                     # Assessment logic and analysis modules
│   ├── analysis/             # Namespace and workload analysis
│   ├── tools/                # Artifact inspection helpers
│   ├── __main__.py           # CLI entry point
│   ├── agent.py              # ReAct orchestration loop
│   ├── config.py             # Runtime settings
│   ├── llm.py                # LLM client integration
│   ├── prompts.py            # System and user prompts
│   ├── local_analyze.py      # Local offline assessment runner
│   └── report.py             # Report builder
├── helm/kubeoptix-analyzer/  # Helm chart for OpenShift deployment
│   ├── templates/            # Kubernetes manifests
│   ├── Chart.yaml            # Chart metadata
│   ├── values.yaml           # Default chart values
│   └── values.example.yaml   # Example deployment configuration
├── api.py                    # HTTP service API
├── Containerfile             # Container image definition
├── install.sh                # OpenShift install helper
├── cleanup-ocp.sh            # Post-install cleanup utility
├── run.sh                    # Local CLI bootstrap script
├── run-ocp.sh               # Minimal entry script for OpenShift runtime
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── .env.example              # Example environment config (if present in the repo)
└── data/                     # Runtime data directory expected at runtime
```

## Configuration

The CLI reads environment settings from `.env` in the project root. The project expects keys such as:

```dotenv
CURSOR_API_KEY=
CURSOR_MODEL=composer-2.5

# Optional OpenAI-compatible provider
# LLM_API_KEY=
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o-mini
```

Additional runtime settings may be provided for embedded analysis, for example:

```dotenv
EMBEDDED_BASE_URL=http://127.0.0.1:11434/v1
EMBEDDED_API_KEY=ollama
EMBEDDED_MODEL=mistral
EMBEDDED_TIMEOUT_S=120
```

The Helm chart exposes runtime configuration through `values.yaml`:

- `build.enabled` and `build.git.*` for the OpenShift image build
- `secretEnv.*` for runtime credentials
- `service.api.*` for the Service definition
- `persistence.*` for storage configuration
- `resources.*` for CPU and memory requests/limits
- `podEnv.*` for environment variables in the workload

The API runtime directories are fixed:

- `/app/data/assessment`
- `/app/data/reports`

The `api.py` service accepts a POST request to `/run` with `mode` and `namespaces`, and exposes a `GET /status` endpoint for progress reporting.

## Installation

Install dependencies for local execution:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Deploy to OpenShift with the existing Helm chart:

```bash
helm upgrade --install kubeoptix-analyzer ./helm/kubeoptix-analyzer \
  --namespace shiftwise-ai \
  --create-namespace \
  -f ./helm/kubeoptix-analyzer/values.example.yaml
```

The repository also ships with an installer helper:

```bash
./install.sh -f ./helm/kubeoptix-analyzer/values.example.yaml
```

## Helm Configuration

The chart name is `kubeoptix-analyzer` and it deploys the application on OpenShift by creating the following primary resources:

- `StatefulSet` for the analyzer runtime
- `Service` for the API endpoint
- `ImageStream` and `BuildConfig` when build automation is enabled
- optional `Secret` creation for runtime environment variables
- optional persistent storage when `persistence.enabled` is set

Key values in the chart include:

```yaml
deploy:
  enabled: true

service:
  api:
    enabled: true
    name: analyzer-api
    type: ClusterIP
    port: 8000
    targetPort: 8000

build:
  enabled: true
  registryHost: image-registry.openshift-image-registry.svc:5000
  imageStreamName: ""
  outputTag: latest
  containerfilePath: Containerfile
  git:
    uri: ""
    ref: main
    sourceSecret: ""

secretEnv:
  create: false
  name: ""
  cursorApiKey: ""
  cursorModel: composer-2.5
  llmApiKey: ""
  llmBaseUrl: https://api.openai.com/v1
  llmModel: gpt-4o-mini
```

`install.sh` also supports post-install cleanup options for orphaned OpenShift resources. Those are optional and can be disabled or restricted with environment variables such as `POST_INSTALL_CLEANUP`, `CLEANUP_DRY_RUN`, and `CLEANUP_TARGET_KINDS`.

## Running Locally

The local execution path is driven by the project scripts:

```bash
./run.sh --help
./run.sh --artifacts ./data/assessment --mode local --report ./data/reports
```

The analyzer expects a prepared artifact tree similar to:

```text
<artifacts>/
  worknodes/
  <namespace>/
    resources/
    pods-logs/
```

The output report is written to the selected report path or to the default generated report inside the artifact directory.

## Development

To prepare a development environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Then run the analyzer directly:

```bash
python -m agent --artifacts ./data/assessment --mode local
```

The repository does not include a dedicated test suite in the visible project tree, so validation is primarily done through CLI execution, artifact inspection, and deployment checks.

## Container

The project contains a `Containerfile` that builds the analyzer runtime image. The runtime is designed to read artifact directories from `/app/data` and writes generated reports to `/app/data/reports`.

Build the image from the repository root:

```bash
podman build -t kubeoptix-analyzer .
```

## Deployment

The application is deployed in OpenShift with the Helm chart under `helm/kubeoptix-analyzer`. The chart creates the runtime workload and service, and it can optionally build the image from source with OpenShift `BuildConfig` and `ImageStream` resources.

The installation flow in `install.sh` performs a two-phase deployment:

1. Deploy build resources and trigger the OpenShift image build.
2. Deploy the runtime workload and verify the service is healthy.

## Troubleshooting

- If the artifact directory is missing or malformed, the analyzer exits with a clear path error.
- If `.env` is missing or both `CURSOR_API_KEY` and `LLM_API_KEY` are empty, the runtime stops before the analysis begins.
- If the Helm installation cannot find the release namespace or build config, verify the namespace exists and the chart was installed with the correct values file.
- If the application fails health checks, inspect the pod logs and the service proxy status in OpenShift.

## License

No explicit license file was identified in this repository, so no license is documented here.

When you run the wrapper script for the first time, it will:

1. Resolve the project root.
2. Create `.venv/` if it does not exist.
3. Activate the virtual environment.
4. Upgrade `pip`.
5. Install dependencies from `requirements.txt`.
6. Start `python -m agent` with the same CLI arguments.

### 3. Run the analyzer

Local mode:

```bash
./run.sh --artifacts ./artifacts
```

LLM mode:

```bash
./run.sh --artifacts ./artifacts --mode llm
```

Embedded mode:

```bash
./run.sh --artifacts ./artifacts --mode embedded
```

Custom locale:

```bash
./run.sh --artifacts ./artifacts --mode local --locale en-US
./run.sh --artifacts ./artifacts --mode embedded --locale es-ES
./run.sh --artifacts ./artifacts --mode llm --locale it-IT
```

Custom report path:

```bash
./run.sh --artifacts ./artifacts --report ./out/assessment-report.md
```

### 4. Choose the analysis mode

`local`

- deterministic analysis without external LLM calls
- scans manifests, routes, services, ConfigMaps, logs, operators, HPAs, and worker-node capacity
- writes one Markdown report directly from local heuristics
- translates the final Markdown to the locale selected with `--locale`

`llm`

- validates that `.env` exists and contains credentials
- if `CURSOR_API_KEY` is set, uses Cursor SDK
- otherwise, if `LLM_API_KEY` is set, uses an OpenAI-compatible API and a tool-driven ReAct loop
- writes a single Markdown report to the artifact directory or the path passed with `--report`
- instructs the model to answer in the locale selected with `--locale`

`embedded`

- runs the deterministic local analysis first
- computes heuristic classification + reranking of findings
- clusters repeated log errors by normalized signature
- scores workload risk using findings, logs, QoS, missing limits/requests, and replica posture
- detects requests/limits outliers with IQR-based analysis
- sends only the compact evidence summary to a local OpenAI-compatible model such as Ollama + Mistral
- translates the final Markdown to the locale selected with `--locale`

### 5. Review the output

By default, the generated file is:

```text
<artifacts>/assessment-report.md
```

The report covers inventory, topology, resources, observability, ConfigMap security checks, findings, action plan, and references.

## Internal analyzer flow

```mermaid
flowchart TD
    A[Prepared artifacts directory] --> B[run.sh]
    B --> C[Create or reuse .venv]
    C --> D[Install dependencies]
    D --> E[python -m agent]
    E --> F{Mode}

    F -->|local| G[Discover namespaces and worknodes]
    G --> H[Parse YAML manifests and logs]
    H --> I[Run local analysis modules]
    I --> J[Write assessment-report.md]

    F -->|llm| K[Validate .env and credentials]
    K --> L{Provider}
    L -->|Cursor| M[Cursor SDK prompt over artifact directory]
    L -->|OpenAI-compatible| N[Inventory artifacts and expose local tools]
    N --> O[Tool-driven ReAct loop]
    F -->|embedded| Q[Run deterministic local analysis]
    Q --> R[Heuristic reranking and workload risk scoring]
    R --> S[Log clustering and resource outlier detection]
    S --> T[Compact evidence summary to local OpenAI-compatible model]
    M --> P[Write Markdown report]
    O --> P
    T --> P
```

## What local mode analyzes

- namespace discovery
- application inventory
- topology inferred from Deployments, Services, Routes, and ConfigMaps
- CPU and memory requests and limits
- worker-node allocatable and capacity totals
- HPA and observability-related resources
- log error patterns such as crashes, OOM, timeouts, and connection failures
- risky configuration patterns in manifests and ConfigMaps
- operator inventory from CSVs, Subscriptions, and PackageManifests

## Main commands

Show CLI help:

```bash
python -m agent --help
```

Run local analysis directly:

```bash
python -m agent --artifacts ./artifacts --mode local
```

Run LLM analysis directly:

```bash
python -m agent --artifacts ./artifacts --mode llm
```

Run embedded analysis directly:

```bash
python -m agent --artifacts ./artifacts --mode embedded
```

Run with a specific report locale:

```bash
python -m agent --artifacts ./artifacts --mode local --locale en-US
```

## Notes

- The analyzer is offline with respect to cluster access. It only reads local artifacts.
- The quality of the report depends on the completeness of the collected artifacts.
- LLM mode does not replace artifact sanitization. Sensitive-data removal should happen upstream in the harvester pipeline.
