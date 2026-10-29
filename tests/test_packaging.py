"""Build and offline dependency-resolution checks for both distributions.

Requires the release build tools. Third-party wheels used by the resolver tests
contain metadata only; these checks do not exercise the scientific or Qt APIs.
"""

import base64
import configparser
import csv
from email import message_from_bytes
import hashlib
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
import venv
from zipfile import ZipFile

from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parents[1]


def run(command, *, cwd=None, env=None):
    result = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode:
        raise AssertionError(
            f"Command failed: {command}\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def wheel_metadata(path):
    with ZipFile(path) as archive:
        name = next(
            name for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
        )
        return message_from_bytes(archive.read(name))


def write_stub_wheel(directory, requirement):
    """Create a valid, metadata-only wheel for offline resolver checks."""
    version = "9999"
    if not requirement.specifier.contains(version):
        raise AssertionError(f"Update stub version for {requirement}")
    return write_fixture_wheel(directory, requirement.name, version, {})


def write_fixture_wheel(directory, distribution, version, files):
    name = re.sub(r"[-_.]+", "_", distribution).lower()
    info = f"{name}-{version}.dist-info"
    files = dict(files)
    files.update({
        f"{info}/METADATA": (
            "Metadata-Version: 2.3\n"
            f"Name: {distribution}\nVersion: {version}\n\n"
        ).encode(),
        f"{info}/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: pyfwat-packaging-test\n"
            "Root-Is-Purelib: true\nTag: py3-none-any\n"
        ).encode(),
    })
    records = io.StringIO(newline="")
    writer = csv.writer(records)
    for path, data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest())
        writer.writerow((path, "sha256=" + digest.decode().rstrip("="), len(data)))
    writer.writerow((f"{info}/RECORD", "", ""))
    files[f"{info}/RECORD"] = records.getvalue().encode()
    wheel = directory / f"{name}-{version}-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
    return wheel


class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="pyfwat-packaging-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.workspace = Path(cls.temporary.name)
        cls.dist = cls.workspace / "dist"
        cls.project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
        cls.version = cls.project["version"]
        run([
            sys.executable,
            ROOT / "scripts/build_distributions.py",
            "--no-isolation",
            "--outdir",
            cls.dist,
        ], cwd=ROOT)
        artifacts = list(cls.dist.iterdir())
        if len(artifacts) != 4:
            raise AssertionError(f"Expected two wheels and two sdists: {artifacts}")
        cls.core = cls.dist / f"pyfwat_core-{cls.version}-py3-none-any.whl"
        cls.full = cls.dist / f"pyfwat-{cls.version}-py3-none-any.whl"
        cls.core_metadata = wheel_metadata(cls.core)
        cls.full_metadata = wheel_metadata(cls.full)
        for text in cls.core_metadata.get_all("Requires-Dist", []):
            write_stub_wheel(cls.dist, Requirement(text))

    def test_metadata_and_file_ownership(self):
        self.assertEqual(self.core_metadata["Name"], "pyfwat-core")
        self.assertEqual(self.full_metadata["Name"], "pyfwat")
        self.assertEqual(self.core_metadata["Version"], self.version)
        self.assertEqual(self.full_metadata["Version"], self.version)
        requirements = [
            Requirement(text)
            for text in self.core_metadata.get_all("Requires-Dist", [])
        ]
        qt = [req for req in requirements if req.name.lower() == "pyside6"]
        self.assertEqual(len(qt), 1)
        self.assertIsNotNone(qt[0].marker)
        self.assertFalse(qt[0].marker.evaluate({"extra": ""}))
        self.assertTrue(qt[0].marker.evaluate({"extra": "gui"}))
        full_requirements = self.full_metadata.get_all("Requires-Dist", [])
        self.assertEqual(len(full_requirements), 1)
        dependency = Requirement(full_requirements[0])
        self.assertEqual(dependency.name, "pyfwat-core")
        self.assertEqual(dependency.extras, {"gui"})
        self.assertEqual(str(dependency.specifier), f"=={self.version}")
        self.assertIsNone(dependency.marker)
        with ZipFile(self.core) as archive:
            names = set(archive.namelist())
            for source in (ROOT / "pyfwat").rglob("*.py"):
                self.assertIn(source.relative_to(ROOT).as_posix(), names)
            for folder in ("data", "cpt"):
                for source in (ROOT / "pyfwat" / folder).iterdir():
                    if source.is_file():
                        self.assertIn(source.relative_to(ROOT).as_posix(), names)
            entry_points = configparser.ConfigParser()
            path = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
            entry_points.read_string(archive.read(path).decode())
            self.assertEqual(dict(entry_points["console_scripts"]), self.project["scripts"])
        with ZipFile(self.full) as archive:
            self.assertTrue(all(".dist-info/" in name for name in archive.namelist()))
            self.assertFalse(any(name.endswith("/entry_points.txt") for name in archive.namelist()))

    def test_sdists_rebuild_without_checkout(self):
        sources = sorted(self.dist.glob("*.tar.gz"))
        self.assertEqual(len(sources), 2)
        for source in sources:
            with self.subTest(source=source.name):
                unpack = self.workspace / (source.name + "-unpacked")
                unpack.mkdir()
                with tarfile.open(source) as archive:
                    archive.extractall(unpack, filter="data")
                project = next(unpack.iterdir())
                output = unpack / "rebuilt"
                run([
                    sys.executable, "-m", "build", "--wheel", "--no-isolation",
                    "--outdir", output,
                ], cwd=project)
                rebuilt = next(output.glob("*.whl"))
                metadata = wheel_metadata(rebuilt)
                original = self.core_metadata if metadata["Name"] == "pyfwat-core" else self.full_metadata
                self.assertEqual(metadata["Version"], self.version)
                self.assertEqual(metadata.get_all("Requires-Dist", []), original.get_all("Requires-Dist", []))

    def check_resolver_install(self, package, *, gui, legacy=None):
        suffix = "-migrated" if legacy is not None else ""
        environment = self.workspace / f"venv-{package}{suffix}"
        venv.EnvBuilder(with_pip=True).create(environment)
        binary = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binary / ("python.exe" if os.name == "nt" else "python")
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("PIP_") and key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        env.update(PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK="1")
        if legacy is not None:
            run([python, "-m", "pip", "install", "--no-index", legacy], cwd=self.workspace, env=env)
            run([python, "-c", "import pyfwat"], cwd=self.workspace, env=env)
            run([python, "-m", "pip", "uninstall", "-y", "pyfwat"], cwd=self.workspace, env=env)
        run([
            python, "-m", "pip", "install", "--no-index", "--find-links",
            self.dist, package,
        ], cwd=self.workspace, env=env)
        run([python, "-m", "pip", "check"], cwd=self.workspace, env=env)
        code = (
            "from importlib.metadata import distributions; import pyfwat; "
            "names = {d.metadata['Name'].lower() for d in distributions()}; "
            "assert 'pyfwat-core' in names; "
            f"assert ('pyside6' in names) is {gui!r}; "
            f"assert ('pyfwat' in names) is {gui!r}"
        )
        run([python, "-c", code], cwd=self.workspace, env=env)
        clean = binary / ("fwat_clean.exe" if os.name == "nt" else "fwat_clean")
        self.assertIn("usage:", run([clean, "--help"], cwd=self.workspace, env=env).lower())
        if gui:
            # Removing/upgrading the wrapper must not delete core-owned code.
            run([python, "-m", "pip", "uninstall", "-y", "pyfwat"], cwd=self.workspace, env=env)
            run([python, "-m", "pip", "check"], cwd=self.workspace, env=env)
            run([python, "-c", "import pyfwat; from importlib.metadata import version; version('pyfwat-core')"], cwd=self.workspace, env=env)
            self.assertIn("usage:", run([clean, "--help"], cwd=self.workspace, env=env).lower())

    def test_core_dependency_resolution_without_qt(self):
        self.check_resolver_install("pyfwat-core", gui=False)

    def test_default_dependency_resolution_with_qt(self):
        self.check_resolver_install("pyfwat", gui=True)

    def test_legacy_clean_migration(self):
        # The old distribution owned these paths directly. Follow the documented
        # uninstall-first migration before giving ownership to pyfwat-core.
        with ZipFile(self.core) as archive:
            files = {
                name: archive.read(name)
                for name in (
                    "pyfwat/__init__.py",
                    "pyfwat/postproc/__init__.py",
                    "pyfwat/postproc/clean.py",
                )
            }
        files["pyfwat-0.0.0.dist-info/entry_points.txt"] = (
            "[console_scripts]\nfwat_clean = pyfwat.postproc.clean:main\n"
        ).encode()
        legacy = write_fixture_wheel(self.dist, "pyfwat", "0.0.0", files)
        self.check_resolver_install("pyfwat", gui=True, legacy=legacy)


if __name__ == "__main__":
    unittest.main()
