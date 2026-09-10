import io
import runpy
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

import build_helpers.verify_distribution_licenses as verifier
from build_helpers.verify_distribution_licenses import main, read_antlr_license

LICENSE_PATH = "ATTRIBUTION/LICENSE-antlr4"
LICENSE_TEXT = b"ANTLR license text"


def test_read_antlr_license_from_wheel(tmp_path: Path) -> None:
    wheel = tmp_path / "omegaconf-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"omegaconf-1.0.dist-info/licenses/{LICENSE_PATH}", LICENSE_TEXT
        )

    assert read_antlr_license(wheel) == LICENSE_TEXT


def test_read_antlr_license_from_sdist(tmp_path: Path) -> None:
    sdist = tmp_path / "omegaconf-1.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        member = tarfile.TarInfo(f"omegaconf-1.0/{LICENSE_PATH}")
        member.size = len(LICENSE_TEXT)
        archive.addfile(member, io.BytesIO(LICENSE_TEXT))

    assert read_antlr_license(sdist) == LICENSE_TEXT


def test_missing_antlr_license_is_rejected(tmp_path: Path) -> None:
    wheel = tmp_path / "omegaconf-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w"):
        pass

    with pytest.raises(RuntimeError, match="ANTLR license missing"):
        read_antlr_license(wheel)


def test_missing_antlr_license_is_rejected_from_sdist(tmp_path: Path) -> None:
    sdist = tmp_path / "omegaconf-1.0.tar.gz"
    with tarfile.open(sdist, "w:gz"):
        pass

    with pytest.raises(RuntimeError, match="ANTLR license missing"):
        read_antlr_license(sdist)


def test_unsupported_distribution_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Unsupported distribution artifact"):
        read_antlr_license(tmp_path / "omegaconf-1.0.zip")


def test_main_requires_artifacts() -> None:
    with pytest.raises(RuntimeError, match="No distribution artifacts provided"):
        main([])


def test_main_verifies_matching_license(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    license_path = tmp_path / LICENSE_PATH
    license_path.parent.mkdir()
    license_path.write_bytes(LICENSE_TEXT)
    monkeypatch.setattr(verifier, "REPOSITORY_ROOT", tmp_path)

    wheel = tmp_path / "omegaconf-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"omegaconf-1.0.dist-info/licenses/{LICENSE_PATH}", LICENSE_TEXT
        )

    main([str(wheel)])

    assert capsys.readouterr().out == f"Verified ANTLR license in {wheel}\n"


def test_main_rejects_different_license(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    license_path = tmp_path / LICENSE_PATH
    license_path.parent.mkdir()
    license_path.write_bytes(LICENSE_TEXT)
    monkeypatch.setattr(verifier, "REPOSITORY_ROOT", tmp_path)

    wheel = tmp_path / "omegaconf-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"omegaconf-1.0.dist-info/licenses/{LICENSE_PATH}", b"different"
        )

    with pytest.raises(RuntimeError, match="ANTLR license differs"):
        main([str(wheel)])


def test_module_entry_point_requires_artifacts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(Path(verifier.__file__))])

    with pytest.raises(RuntimeError, match="No distribution artifacts provided"):
        runpy.run_path(str(verifier.__file__), run_name="__main__")
