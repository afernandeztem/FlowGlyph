"""Finding iFlow artifacts: exported `.zip` files, unpacked folders and bare `.iflw` files."""

from pathlib import Path

from flowglyph.adapters.sap_cpi.bundle import manifest_type, read_zip
from flowglyph.errors import AdapterError


def find_artifacts(path: Path) -> list[Path]:
    """Exported `.zip` artifacts and unpacked artifact folders under `path`."""
    if path.is_file():
        is_zip = path.suffix == ".zip" and _is_artifact_zip(path)
        return [path] if is_zip or path.suffix == ".iflw" else []
    if not path.is_dir():
        return []
    found: list[Path] = []
    for manifest in sorted(path.rglob("META-INF/MANIFEST.MF")):
        root = manifest.parent.parent
        if manifest_type(manifest.read_bytes()) and any(root.rglob("*.iflw")):
            found.append(root)
    unpacked = set(found)
    found.extend(
        file
        for file in sorted(path.rglob("*.zip"))
        if not any(folder in file.parents for folder in unpacked) and _is_artifact_zip(file)
    )
    found.extend(
        file
        for file in sorted(path.rglob("*.iflw"))
        if not any(folder in file.parents for folder in unpacked)
    )
    return found


def _is_artifact_zip(path: Path) -> bool:
    try:
        bundle = read_zip(path, path.name)
    except AdapterError:
        return False
    return bool(bundle.iflows) or bundle.bundle_type not in {"", "IntegrationFlow"}
