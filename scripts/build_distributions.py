#!/usr/bin/env python3
"""Build the core distribution and the default GUI metapackage together."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

try:
    import tomllib
except ImportError:
    raise SystemExit("Building both distributions requires Python 3.11 or newer.")


ROOT = Path(__file__).resolve().parents[1]


def toml_value(value):
    """Serialize the JSON-compatible values used in project metadata as TOML."""
    if isinstance(value, dict):
        fields = (
            f"{json.dumps(key)} = {toml_value(item)}"
            for key, item in value.items()
        )
        return "{ " + ", ".join(fields) + " }"
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def write_metapackage(directory, config):
    project = dict(config["project"])
    if project["name"] != "pyfwat-core":
        raise ValueError("The root project must be named pyfwat-core.")
    project["name"] = "pyfwat"
    project["dependencies"] = [f"pyfwat-core[gui]=={project['version']}"]
    # Preserve old pyfwat[gui] commands; the wrapper always requests GUI support.
    project["optional-dependencies"] = {"gui": []}
    project.pop("scripts", None)

    # Make the generated sdist independent of this repository's directory layout.
    project["readme"] = "README.md"
    (directory / "README.md").write_text(
        (ROOT / config["project"]["readme"]).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sections = {
        "build-system": config["build-system"],
        "project": project,
        "tool.setuptools": {"packages": []},
    }
    text = "\n\n".join(
        f"[{section}]\n" + "\n".join(
            f"{json.dumps(key)} = {toml_value(value)}"
            for key, value in values.items()
        )
        for section, values in sections.items()
    )
    (directory / "pyproject.toml").write_text(text + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outdir", type=Path, default=ROOT / "dist",
        help="Output directory for both wheels and source distributions.",
    )
    parser.add_argument(
        "--no-isolation", action="store_true",
        help="Use build dependencies already installed in this environment.",
    )
    args = parser.parse_args()
    with (ROOT / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)

    command = [sys.executable, "-m", "build", "--outdir", str(args.outdir.resolve())]
    if args.no_isolation:
        command.append("--no-isolation")

    # Build sequentially: setuptools writes metadata into each source tree.
    subprocess.run(command + [str(ROOT)], check=True)
    with tempfile.TemporaryDirectory(prefix="pyfwat-meta-") as temporary:
        directory = Path(temporary)
        write_metapackage(directory, config)
        subprocess.run(command + [str(directory)], check=True)


if __name__ == "__main__":
    main()
