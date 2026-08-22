#!/usr/bin/env bash
set -euo pipefail

# Post-install cleanup for OpenShift resources associated with a Helm release.
# It deletes resources tagged with the release label that are no longer present
# in the current Helm manifest (orphans).

RELEASE="${RELEASE:-kubeoptix-analyzer}"
NS="${NS:-shiftwise-ai}"
DRY_RUN="${DRY_RUN:-true}"
TARGET_KINDS="${TARGET_KINDS:-configmap,secret,certificate,certificaterequest,order,challenge}"

usage() {
  cat <<EOF
Usage:
  RELEASE=<release> NS=<namespace> [DRY_RUN=true|false] [TARGET_KINDS=kind1,kind2] $0

Examples:
  RELEASE=kubeoptix-analyzer NS=shiftwise-ai DRY_RUN=true $0
  RELEASE=kubeoptix-analyzer NS=shiftwise-ai DRY_RUN=false TARGET_KINDS=configmap,secret $0
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

command -v oc >/dev/null 2>&1 || { echo "[ERROR] oc not found"; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "[ERROR] helm not found"; exit 1; }
command -v awk >/dev/null 2>&1 || { echo "[ERROR] awk not found"; exit 1; }
command -v sort >/dev/null 2>&1 || { echo "[ERROR] sort not found"; exit 1; }
command -v comm >/dev/null 2>&1 || { echo "[ERROR] comm not found"; exit 1; }

oc whoami >/dev/null

if [[ "$DRY_RUN" != "true" && "$DRY_RUN" != "false" ]]; then
  echo "[ERROR] DRY_RUN must be true or false"
  exit 1
fi

echo "[INFO] Cleanup release: $RELEASE"
echo "[INFO] Cleanup namespace: $NS"
echo "[INFO] Dry-run: $DRY_RUN"
echo "[INFO] Target kinds: $TARGET_KINDS"

TMP_DIR="$(mktemp -d)"
EXPECTED_FILE="$TMP_DIR/expected.txt"
LIVE_FILE="$TMP_DIR/live.txt"
ORPHANS_FILE="$TMP_DIR/orphans.txt"

cleanup_tmp() {
  rm -rf "$TMP_DIR"
}
trap cleanup_tmp EXIT

helm get manifest "$RELEASE" -n "$NS" >"$TMP_DIR/manifest.yaml"

awk '
function flush_obj() {
  if (kind != "" && name != "") {
    ns = (namespace != "" ? namespace : "_cluster")
    print tolower(kind) "|" ns "|" name
  }
  kind = ""
  name = ""
  namespace = ""
  in_meta = 0
}

/^---/ {
  flush_obj()
  next
}

$1 == "kind:" {
  kind = $2
  gsub(/\"/, "", kind)
  next
}

$1 == "metadata:" {
  in_meta = 1
  next
}

in_meta && $1 == "name:" {
  name = $2
  gsub(/\"/, "", name)
  next
}

in_meta && $1 == "namespace:" {
  namespace = $2
  gsub(/\"/, "", namespace)
  next
}

in_meta && $0 ~ /^[^[:space:]]/ && $1 != "metadata:" {
  in_meta = 0
}

END {
  flush_obj()
}
' "$TMP_DIR/manifest.yaml" | sort -u >"$EXPECTED_FILE"

IFS=',' read -r -a kinds <<<"$TARGET_KINDS"
selector="app.kubernetes.io/instance=${RELEASE}"

for kind in "${kinds[@]}"; do
  kind="$(echo "$kind" | xargs)"
  [[ -z "$kind" ]] && continue

  out="$(oc get "$kind" -n "$NS" -l "$selector" -o custom-columns=KIND:.kind,NAME:.metadata.name --no-headers 2>/dev/null || true)"
  if [[ -z "$out" ]]; then
    continue
  fi

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    obj_kind="$(echo "$line" | awk '{print tolower($1)}')"
    obj_name="$(echo "$line" | awk '{print $2}')"
    [[ -z "$obj_kind" || -z "$obj_name" ]] && continue
    echo "$obj_kind|$NS|$obj_name" >>"$LIVE_FILE"
  done <<<"$out"
done

sort -u "$LIVE_FILE" -o "$LIVE_FILE" 2>/dev/null || true

if [[ ! -s "$LIVE_FILE" ]]; then
  echo "[INFO] No matching resources found to evaluate."
  exit 0
fi

comm -23 "$LIVE_FILE" "$EXPECTED_FILE" >"$ORPHANS_FILE" || true

if [[ ! -s "$ORPHANS_FILE" ]]; then
  echo "[INFO] No orphan resources found."
  exit 0
fi

echo "[INFO] Orphan resources identified:"
cat "$ORPHANS_FILE" | while IFS='|' read -r orphan_kind orphan_ns orphan_name; do
  if [[ "$orphan_ns" == "_cluster" ]]; then
    echo "  - ${orphan_kind}/${orphan_name}"
  else
    echo "  - ${orphan_kind}/${orphan_name} (ns=${orphan_ns})"
  fi
done

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[INFO] Dry-run enabled. No resources were deleted."
  exit 0
fi

echo "[INFO] Deleting orphan resources..."
while IFS='|' read -r orphan_kind orphan_ns orphan_name; do
  if [[ "$orphan_ns" == "_cluster" ]]; then
    oc delete "$orphan_kind" "$orphan_name" --ignore-not-found=true
  else
    oc -n "$orphan_ns" delete "$orphan_kind" "$orphan_name" --ignore-not-found=true
  fi
done <"$ORPHANS_FILE"

echo "[INFO] Cleanup finished successfully."