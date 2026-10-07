# kubeoptix-analyzer

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch workflow and contribution process.

`kubeoptix-analyzer` is an OpenShift and Kubernetes assessment tool that reads previously collected workload artifacts, inspects their configuration and runtime metadata, and produces a Markdown report with findings, risks, visualizations, and suggested remediation actions.

The project is designed for artifact-based analysis rather than live cluster mutation. It does not query or modify a cluster during analysis. It expects pre-collected manifests, logs, and worker-node inventory to already exist in a structured directory before execution. The analyzer then reviews workloads, services, routes, ConfigMaps, operators, resource sizing, and observability data to identify configuration and reliability issues.

The application has two entry points:

- a CLI (`python -m agent`) for local or batch analysis;
- an HTTP service (`api.py`) for OpenShift integrations and progress polling.

Both entry points invoke the same report-generation pipeline. The API runs one namespace at a time in sequence and writes one Markdown report per namespace.

## Features

- Parses Kubernetes and OpenShift YAML manifests from collected artifacts.
- Evaluates workloads, services, routes, ConfigMaps, and operators for configuration risk.
- Reviews CPU and memory requests/limits, HPA signals, and node capacity.
- Identifies missing readiness/liveness probes, insecure routes, and common misconfigurations.
- Scans logs for error patterns and observability gaps.
- Generates PNG visualizations and embeds them into the Markdown report.
- Produces a Markdown assessment report for a namespace or for all discovered namespaces.
- Runs as a CLI or through an HTTP API in a containerized OpenShift deployment.

## Analysis Flow

```text
Collected artifacts
  |
  v
Layout discovery and YAML/log inspection
  |
  v
Pre-generated visualizations + LLM analysis
  |
  v
Markdown report with embedded PNGs
```

The LLM provider is selected in this order for the CLI: Cursor SDK when `CURSOR_API_KEY` is available, OpenAI-compatible API when `LLM_API_KEY` is available, or Cursor SDK explicitly with `--llm`. The API delegates provider selection to the same CLI script.

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
│   ├── local_analyze.py      # Report path helpers and local analysis utilities
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
├── .env.example              # Local environment template
└── data/                     # Runtime data directory expected at runtime
```

## Configuration

In OpenShift, runtime credentials are loaded from the platform API:

- `GET {SYSTEM_SETTINGS_URL}/system-settings`
- fields used: `cursorApiKey`, `cursorModel`, `llmApiKey`, `llmModel`, `status`

For local development, copy `.env.example` to `.env` and configure one provider:

```dotenv
SYSTEM_SETTINGS_URL=http://localhost:8000

# Cursor SDK provider
CURSOR_API_KEY=
CURSOR_MODEL=composer-2.5

# OpenAI-compatible provider
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

`SYSTEM_SETTINGS_URL` points to a service exposing `GET /system-settings`. The analyzer reads `cursorApiKey`, `cursorModel`, `llmApiKey`, `llmModel`, and `status` from its JSON response. When the URL is configured locally but unavailable, the application warns and falls back to `.env`. In a container or OpenShift, an unreachable or missing system-settings service stops startup rather than silently continuing.

The following runtime variables are also supported:

| Variable | Default | Purpose |
| --- | --- | --- |
| `KUBEOPTIX_API_HOST` | `0.0.0.0` | HTTP bind address |
| `KUBEOPTIX_API_PORT` | `8000` | HTTP port |
| `KUBEOPTIX_RUN_SCRIPT` | `run-ocp.sh` | Script invoked by the API for each namespace |
| `KUBEOPTIX_API_TIMEOUT_S` | `7200` | Per-namespace API execution timeout |
| `KUBEOPTIX_PROGRESS_WINDOW_S` | `18` | Estimated progress window for each phase |
| `AGENT_MAX_ITERATIONS` | `20` | Maximum LLM/tool iterations |
| `AGENT_MAX_FILE_CHARS` | `20000` | Maximum file content read by the agent |
| `SYSTEM_SETTINGS_TIMEOUT_S` | `30` | System Settings API timeout |

The Helm chart exposes runtime configuration through `values.yaml`:

- `build.enabled` and `build.git.*` for the OpenShift image build
- `systemSettings.url` for the platform System Settings API base URL
- `service.api.*` for the Service definition
- `persistence.*` for storage configuration
- `resources.*` for CPU and memory requests/limits
- `podEnv.*` for environment variables in the workload

The API runtime directories are fixed:

- assessment input: `data/assessment` relative to the application root (in the container, `/app/data/assessment`);
- report output: `/app/data/reports`.

The Helm persistence volume is mounted at `/app/data`, so it must contain the assessment folders and should be enabled when reports or collected artifacts must survive pod replacement.

## Artifact Layout

The API discovers namespace directories below `data/assessment`, excluding the reserved `worknodes/` directory. The CLI accepts either a directory containing one namespace or a directory containing multiple namespaces.

Canonical layout:

```text
data/assessment/
├── worknodes/                         # Optional worker-node YAML/inventory
└── my-namespace/
  ├── resources/
  │   ├── deployments.apps/
  │   ├── services/
  │   ├── routes.route.openshift.io/
  │   ├── configmaps/
  │   ├── pods/
  │   ├── horizontalpodautoscalers.autoscaling/
  │   ├── clusterserviceversions.operators.coreos.com/
  │   ├── subscriptions.operators.coreos.com/
  │   └── packagemanifests.packages.operators.coreos.com/
  └── pods-logs/                     # .log and .txt files
```

The analyzer also supports the legacy `apps/<application>/<resource-type>/` layout and `pod-logs/`. YAML files are deduplicated when both layouts contain the same Kubernetes object. If no recognizable namespace subdirectory exists, the CLI treats the input directory itself as one namespace.

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

`install.sh` requires both `helm` and `oc`, an authenticated OpenShift session, an existing `shiftwise-ai` namespace (or the namespace selected through the script environment), and a values file. By default it performs two phases: it deploys the `BuildConfig`/`ImageStream`, starts a binary build from the local workspace, then deploys the `StatefulSet` and checks `/health` through the Service. Git source settings are passed to Helm, but local binary build mode is enabled by default (`BUILD_FROM_LOCAL=true`).

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

systemSettings:
  url: "http://configurations-api:8000"

env:
  LLM_BASE_URL: https://api.openai.com/v1
```

`install.sh` also supports post-install cleanup options for orphaned OpenShift resources. Those are optional and can be disabled or restricted with environment variables such as `POST_INSTALL_CLEANUP`, `CLEANUP_DRY_RUN`, and `CLEANUP_TARGET_KINDS`.

## Running Locally

The local execution path is driven by the project scripts:

```bash
./run.sh --help
./run.sh --artifacts ./data/assessment --report ./data/reports
```

The report argument can be either a Markdown file or an output directory. If omitted, the default is `<artifacts>/assessment-report.md`. `run.sh` creates `.venv` when needed and installs `requirements.txt` on every invocation; use `python -m agent` directly when dependencies are already installed.

Examples:

```bash
# Cursor SDK provider selected automatically when CURSOR_API_KEY is set
./run.sh --artifacts ./data/assessment --report ./data/reports/assessment.md

# Force Cursor SDK provider
./run.sh --llm --artifacts ./data/assessment --report ./data/reports/assessment.md
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

## HTTP API

Start the service locally with:

```bash
python api.py
```

The service listens on `http://0.0.0.0:8000` by default. It exposes:

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status":"ok"}` |
| `GET` | `/status` | Returns the current progress as a plain integer from 0 to 100 |
| `GET` | `/analysis/status` | Returns the richer structured status payload including progress, phase, and current file |
| `GET` | `/assessment/folders` or `/assessment/namespaces` | Lists namespace folders under the assessment directory |
| `GET` | `/reports` or `/reports/files` | Lists generated report files and timestamps |
| `POST` | `/run` | Analyzes one or more namespaces sequentially |
| `DELETE` | `/reports` | Deletes all entries in the report directory |

Run an analysis by sending either a comma-separated string or a JSON array. The request is rejected when a namespace does not exist or another analysis is already running:

```bash
curl -X POST http://localhost:8000/run \
  -H 'Content-Type: application/json' \
  -d '{"namespaces":["my-namespace","another-namespace"]}'
```

The response contains the selected namespaces, input/output directories, invoked command, exit code, stdout, stderr, and report path for each namespace. A successful run returns HTTP 200; a run with one or more namespace failures returns HTTP 500. Poll `/status` for the legacy integer while `/analysis/status` exposes the richer phase and current file details; use `/reports` to discover generated files.

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
python -m agent --artifacts ./data/assessment
```

Run the available test suite with:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

The tests currently focus on Markdown image embedding. End-to-end LLM analysis and OpenShift deployment checks require credentials, prepared artifacts, and a cluster, so they are not run as part of the local unit test command.

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
- If `SYSTEM_SETTINGS_URL` is unreachable, returns inactive status, or provides no usable credentials in OpenShift, inspect the configuration service and its `/system-settings` response.
- If no credentials are available, set `CURSOR_API_KEY` or `LLM_API_KEY`; `--llm` specifically requires `CURSOR_API_KEY`.
- If the API reports that a namespace is missing, inspect `/assessment/folders` and verify that the folder name matches exactly.
- If the Helm installation cannot find the release namespace or BuildConfig, verify the namespace exists, `oc whoami` is authenticated, and the chart was installed with the correct values file.
- If the application fails health checks, inspect the pod logs and the service proxy status in OpenShift.
- If reports disappear after a pod restart, enable chart persistence and mount a PVC at `/app/data`.

## License

This project is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full license text.
