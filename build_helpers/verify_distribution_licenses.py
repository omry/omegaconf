import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Sequence

ANTLR_LICENSE = "ATTRIBUTION/LICENSE-antlr4"
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def read_antlr_license(artifact: Path) -> bytes:
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as archive:
            member = next(
                (
                    name
                    for name in archive.namelist()
                    if name.endswith(
                        (
                            f".dist-info/licenses/{ANTLR_LICENSE}",
                            f".dist-info/{Path(ANTLR_LICENSE).name}",
                        )
                    )
                ),
                None,
            )
            if member is None:
                raise RuntimeError(f"ANTLR license missing from {artifact}")
            return archive.read(member)

    if artifact.name.endswith(".tar.gz"):
        with tarfile.open(artifact, "r:gz") as archive:
            member = next(
                (
                    item
                    for item in archive.getmembers()
                    if item.name.endswith(f"/{ANTLR_LICENSE}")
                ),
                None,
            )
            if member is None:
                raise RuntimeError(f"ANTLR license missing from {artifact}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"ANTLR license is not a file in {artifact}")
            return extracted.read()

    raise RuntimeError(f"Unsupported distribution artifact: {artifact}")


def main(artifacts: Sequence[str]) -> None:
    if not artifacts:
        raise RuntimeError("No distribution artifacts provided")

    expected = (REPOSITORY_ROOT / ANTLR_LICENSE).read_bytes()
    for value in artifacts:
        artifact = Path(value)
        if read_antlr_license(artifact) != expected:
            raise RuntimeError(f"ANTLR license differs in {artifact}")
        print(f"Verified ANTLR license in {artifact}")


if __name__ == "__main__":
    main(sys.argv[1:])
