from __future__ import annotations

import base64
import re
import tempfile
from pathlib import Path
from typing import Any

import hcl2
import httpx

# Attributes relevant to cost optimisation per resource type
_COST_ATTRS: dict[str, list[str]] = {
    "digitalocean_droplet": ["size", "region", "image"],
    "digitalocean_database_cluster": ["size", "engine", "version", "region", "node_count"],
    "digitalocean_kubernetes_cluster": ["region"],
    "digitalocean_loadbalancer": ["size", "region"],
}

_SENSITIVE_PATTERNS = ("token", "key", "secret", "password", "credential")

_SKIP_FILES = {"variables.tf", "outputs.tf", "providers.tf"}


def _unwrap(value: Any) -> Any:
    """python-hcl2 wraps single-item blocks in lists; unwrap them."""
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _load_variable_defaults(tf_dir: Path) -> dict[str, Any]:
    vf = tf_dir / "variables.tf"
    if not vf.exists():
        return {}
    with vf.open() as f:
        parsed = hcl2.load(f)
    defaults: dict[str, Any] = {}
    for block in parsed.get("variable", []):
        for var_name, var_def in block.items():
            defn = _unwrap(var_def)
            if isinstance(defn, dict) and "default" in defn:
                defaults[var_name] = defn["default"]
    return defaults


def _load_sensitive_vars(tf_dir: Path) -> set[str]:
    """Collect variable names marked sensitive=true in variables.tf."""
    vf = tf_dir / "variables.tf"
    if not vf.exists():
        return set()
    with vf.open() as f:
        parsed = hcl2.load(f)
    sensitive: set[str] = set()
    for block in parsed.get("variable", []):
        for var_name, var_def in block.items():
            defn = _unwrap(var_def)
            if isinstance(defn, dict) and defn.get("sensitive"):
                sensitive.add(var_name)
    return sensitive


def _load_tfvars(tf_dir: Path) -> dict[str, Any]:
    tf = tf_dir / "terraform.tfvars"
    if not tf.exists():
        return {}
    with tf.open() as f:
        parsed = hcl2.load(f)
    return {k: (_unwrap(v) if isinstance(v, list) else v) for k, v in parsed.items()}


def _resolve(value: Any, variables: dict[str, Any]) -> Any:
    """Resolve ${var.x} references in a value using the variables map."""
    if not isinstance(value, str):
        return value
    # Whole value is a single var reference
    m = re.fullmatch(r'\$\{var\.(\w+)\}', value.strip())
    if m:
        return variables.get(m.group(1), value)
    # Inline interpolation within a string
    def sub(match: re.Match) -> str:
        return str(variables.get(match.group(1), match.group(0)))
    return re.sub(r'\$\{var\.(\w+)\}', sub, value)


def _extract_var_name(raw: Any) -> str | None:
    """Return the variable name if this value is purely a var reference."""
    if not isinstance(raw, str):
        return None
    m = re.fullmatch(r'\$\{var\.(\w+)\}', raw.strip())
    return m.group(1) if m else None


def _is_sensitive(name: str, sensitive_vars: set[str]) -> bool:
    if name in sensitive_vars:
        return True
    return any(p in name.lower() for p in _SENSITIVE_PATTERNS)


def parse_terraform_dir(tf_dir: str | Path) -> dict[str, Any]:
    """
    Parse a Terraform config directory into a JSON-serialisable dict.

    Returns:
        {
            "variables": { <non-sensitive var name>: <resolved value>, ... },
            "resources": [
                {
                    "type": "digitalocean_droplet",
                    "name": "app",
                    "size": "s-1vcpu-1gb",
                    "size_var": "droplet_size",   # which tfvar controls this field
                    ...
                },
                ...
            ]
        }
    """
    tf_path = Path(tf_dir)

    defaults = _load_variable_defaults(tf_path)
    tfvars = _load_tfvars(tf_path)
    sensitive_vars = _load_sensitive_vars(tf_path)

    # tfvars override defaults
    variables: dict[str, Any] = {**defaults, **tfvars}

    resources: list[dict[str, Any]] = []

    for tf_file in sorted(tf_path.glob("*.tf")):
        if tf_file.name in _SKIP_FILES:
            continue
        with tf_file.open() as f:
            parsed = hcl2.load(f)

        for resource_block in parsed.get("resource", []):
            for rtype, instances in resource_block.items():
                for rname, body in instances.items():
                    body = _unwrap(body)
                    if not isinstance(body, dict):
                        continue
                    relevant_keys = _COST_ATTRS.get(rtype)
                    if relevant_keys is None:
                        continue
                    entry: dict[str, Any] = {"type": rtype, "name": rname}
                    for key in relevant_keys:
                        raw = body.get(key)
                        if raw is None:
                            continue
                        entry[key] = _resolve(raw, variables)
                        var_name = _extract_var_name(raw)
                        if var_name:
                            entry[f"{key}_var"] = var_name
                    resources.append(entry)

    safe_variables = {
        k: v for k, v in variables.items()
        if not _is_sensitive(k, sensitive_vars)
    }

    return {"variables": safe_variables, "resources": resources}


async def parse_terraform_from_github(
    owner: str, repo: str, branch: str, token: str
) -> dict[str, Any]:
    """Fetch .tf / .tfvars files from a GitHub repo and parse them."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get recursive tree to find all .tf / .tfvars files
        tree_res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}",
            headers=headers,
            params={"recursive": "1"},
        )
        tree_res.raise_for_status()
        entries = tree_res.json().get("tree", [])

        tf_paths = [
            e["path"] for e in entries
            if e.get("type") == "blob"
            and (e["path"].endswith(".tf") or e["path"].endswith(".tfvars"))
        ]

        # Fetch each file's content
        file_contents: dict[str, str] = {}
        for path in tf_paths:
            res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers=headers,
                params={"ref": branch},
            )
            if res.status_code != 200:
                continue
            payload = res.json()
            if payload.get("encoding") == "base64" and payload.get("content"):
                raw = base64.b64decode(payload["content"])
                file_contents[path] = raw.decode("utf-8", errors="replace")

    # Write to a temp dir and parse
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for path, content in file_contents.items():
            dest = tmp_path / Path(path).name
            dest.write_text(content, encoding="utf-8")
        return parse_terraform_dir(tmp_path)
