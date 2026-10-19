import argparse
import json
import os
from pathlib import Path
import re
import subprocess

import yaml


REPOSITORY = "ShiftWise-AI/kubeoptix-analyzer"
OPERATOR = "ShiftWise-AI/kubeoptix-operator"
IMAGE = "quay.io/parraes/kubeoptix-analyzer"
CHART_PATH = "helm/kubeoptix-analyzer/Chart.yaml"
VALUES_PATH = "helm/kubeoptix-analyzer/values.yaml"
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def api(path, method="GET", payload=None):
    command = ["gh", "api", path, "--method", method]
    if payload is not None:
        command += ["--input", "-"]
    return json.loads(subprocess.check_output(
        command, input=None if payload is None else json.dumps(payload), text=True
    ))


def version_tuple(value):
    if not SEMVER.fullmatch(value):
        raise ValueError(f"Invalid MAJOR.MINOR.PATCH: {value}")
    return tuple(map(int, value.split(".")))


def next_version(current, released):
    baseline = version_tuple(current)
    versions = [version_tuple(value) for value in released]
    if any(value[:2] > baseline[:2] for value in versions):
        raise ValueError("Chart major/minor is older than an existing release")
    patch = max([baseline[2]] + [value[2] for value in versions if value[:2] == baseline[:2]])
    return f"{baseline[0]}.{baseline[1]}.{patch + 1}"


def replace_line(text, pattern, replacement):
    updated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("Expected exactly one matching version field")
    return updated


def replace_chart_version(chart_text, values_text, version):
    version_tuple(version)
    chart = yaml.safe_load(chart_text)
    values = yaml.safe_load(values_text)
    if chart.get("name") != "kubeoptix-analyzer":
        raise ValueError("Unexpected Helm chart name")
    if values.get("image", {}).get("repository") != IMAGE:
        raise ValueError("Unexpected Analyzer image repository")
    if not all((
        chart.get("version") == chart.get("appVersion"),
        chart.get("version") == values.get("image", {}).get("tag"),
        chart.get("version") == values.get("build", {}).get("outputTag"),
    )):
        raise ValueError("Chart and image versions have drifted")

    updated_chart = replace_line(chart_text, r"^version:.*$", f"version: {version}")
    updated_chart = replace_line(
        updated_chart, r"^appVersion:.*$", f'appVersion: "{version}"'
    )
    updated_values = replace_line(values_text, r"^  tag:.*$", f"  tag: {version}")
    updated_values = replace_line(
        updated_values, r"^  outputTag:.*$", f"  outputTag: {version}"
    )

    parsed_chart = yaml.safe_load(updated_chart)
    parsed_values = yaml.safe_load(updated_values)
    if not all((
        parsed_chart["version"] == version,
        parsed_chart["appVersion"] == version,
        parsed_values["image"]["tag"] == version,
        parsed_values["build"]["outputTag"] == version,
    )):
        raise ValueError("Updated chart version fields did not validate")
    return updated_chart, updated_values


def verify_source(source):
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Expected full source commit SHA")
    run("git", "merge-base", "--is-ancestor", source, "origin/main")
    prs = api(f"repos/{REPOSITORY}/commits/{source}/pulls?per_page=100")
    allowed = any(
        pr.get("merged_at")
        and pr.get("merge_commit_sha") == source
        and pr.get("base", {}).get("ref") == "main"
        and (pr.get("base", {}).get("repo") or {}).get("full_name") == REPOSITORY
        and pr.get("head", {}).get("ref") == "develop"
        and (pr.get("head", {}).get("repo") or {}).get("full_name") == REPOSITORY
        for pr in prs
    )
    if not allowed:
        raise ValueError("Release source must be a merged same-repository develop PR to main")


def output(**values):
    with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
        for key, value in values.items():
            stream.write(f"{key}={value}\n")


def reserve(source):
    verify_source(source)
    tags = run("git", "tag", "--list", "v*").splitlines()
    released = [tag[1:] for tag in tags if SEMVER.fullmatch(tag[1:])]
    marker = f"Release-Source: {source}"
    matches = [
        tag for tag in tags
        if SEMVER.fullmatch(tag[1:])
        and marker in run("git", "for-each-ref", "--format=%(contents)", f"refs/tags/{tag}").splitlines()
    ]
    if len(matches) > 1:
        raise ValueError("Multiple releases reserved for the same source")
    if matches:
        tag = matches[0]
        chart = yaml.safe_load(run("git", "show", f"{tag}:{CHART_PATH}"))
        if chart["version"] != tag[1:]:
            raise ValueError("Reserved release version does not match Chart.yaml")
        if run("git", "rev-parse", f"{tag}^1") != source:
            raise ValueError("Reserved release has an unexpected source parent")
    else:
        run("git", "checkout", "--detach", source)
        chart_path = Path(CHART_PATH)
        values_path = Path(VALUES_PATH)
        chart_text = chart_path.read_text()
        values_text = values_path.read_text()
        current = yaml.safe_load(chart_text)["version"]
        version = next_version(current, released)
        updated_chart, updated_values = replace_chart_version(
            chart_text, values_text, version
        )
        chart_path.write_text(updated_chart)
        values_path.write_text(updated_values)
        run("git", "add", CHART_PATH, VALUES_PATH)
        run("git", "commit", "-m", f"Release {version}\n\n{marker}")
        tag = f"v{version}"
        run("git", "tag", "-a", tag, "-m", marker)
        run("git", "push", "origin", f"refs/tags/{tag}")
    run("git", "checkout", "--detach", tag)
    output(version=tag[1:], tag=tag, source=source, commit=run("git", "rev-parse", "HEAD"))


def operator_image(text, reference):
    if not re.fullmatch(r"quay\.io/parraes/kubeoptix-analyzer:[^@\s]+@sha256:[0-9a-f]{64}", reference):
        raise ValueError("Invalid immutable Analyzer image reference")
    updated, count = re.subn(
        r'(?m)^(\s*AnalyzerImage:\s+)(?:registryImage\(constants\.AnalyzerName\)|"[^"\n]+"),$',
        lambda match: f'{match[1]}"{reference}",',
        text,
    )
    if count != 1:
        raise ValueError("Operator AnalyzerImage contract changed; refusing broad edits")
    return updated


def update_operator(version, digest, directory):
    version_tuple(version)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Invalid registry digest")
    reference = f"{IMAGE}:{version}@{digest}"
    root = Path(directory).resolve()
    branch = f"fix/analyzer-{version}"
    remote_branches = run("git", "ls-remote", "--heads", "origin", branch, cwd=root)
    if remote_branches:
        run("git", "fetch", "origin", branch, cwd=root)
        run("git", "checkout", "--detach", "FETCH_HEAD", cwd=root)
    settings_path = root / "internal/operands/settings.go"
    before = settings_path.read_text()
    after = operator_image(before, reference)
    if after != before:
        settings_path.write_text(after)
    probe = root / "internal/operands/ci_release_test.go"
    if probe.exists():
        raise ValueError("Refusing to overwrite an existing Operator test")
    probe.write_text(
        'package operands\nimport "testing"\n'
        'func TestCIReleaseAnalyzerImage(t *testing.T) {\n'
        f'if got := FromCR(newShiftWise()).AnalyzerImage; got != "{reference}" {{\n'
        't.Fatalf("unexpected Analyzer image: %s", got)\n}\n}\n'
    )
    try:
        run("go", "test", "./internal/operands", cwd=root)
    finally:
        probe.unlink()
    changed = run("git", "diff", "--name-only", cwd=root).splitlines()
    if changed not in ([], ["internal/operands/settings.go"]):
        raise ValueError("Unexpected Operator changes")
    if changed:
        run("git", "checkout", "-B", branch, cwd=root)
        run("git", "add", "internal/operands/settings.go", cwd=root)
        run("git", "commit", "-m", f"fix: pin Analyzer to {version}", cwd=root)
        run("git", "push", "origin", f"HEAD:refs/heads/{branch}", cwd=root)
    elif not remote_branches:
        return
    existing = api(
        f"repos/{OPERATOR}/pulls?state=open&head=ShiftWise-AI:{branch}&base=main"
    )
    if not existing:
        api(f"repos/{OPERATOR}/pulls", "POST", {
            "title": f"fix: update Analyzer to {version}",
            "head": branch,
            "base": "main",
            "body": f"Published and verified image: `{reference}`.\n\nOnly the Analyzer image is changed.",
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["reserve", "operator"])
    parser.add_argument("--source")
    parser.add_argument("--version")
    parser.add_argument("--digest")
    parser.add_argument("--directory", default="operator")
    args = parser.parse_args()
    if args.command == "reserve":
        reserve(args.source)
    else:
        update_operator(args.version, args.digest, args.directory)


if __name__ == "__main__":
    main()