import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from build_helpers.verify_distribution_licenses import read_antlr_license

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
