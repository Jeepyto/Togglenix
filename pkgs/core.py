from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Mode = Literal["import"]

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "togglenix"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "modules.json"
DEFAULT_ROOT_PATH = Path("/etc/nixos")


class ToggleError(Exception):
    """Erreur métier : pattern non trouvé, fichier illisible, config invalide..."""


DEFAULT_CATEGORY = "Autres"


@dataclass
class ModuleEntry:
    name: str
    mode: Mode
    file: str
    target: str
    category: str = DEFAULT_CATEGORY
    inverted: bool = False

    def __post_init__(self) -> None:
        if not self.target:
            raise ToggleError(f"Module '{self.name}' nécessite 'target'.")
        if not self.category:
            self.category = DEFAULT_CATEGORY

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "mode": self.mode,
            "file": self.file,
            "target": self.target,
            "category": self.category,
            "inverted": self.inverted,
        }

    @staticmethod
    def from_dict(d: dict) -> "ModuleEntry":
        return ModuleEntry(
            name=d["name"],
            mode=d.get("mode", "import"),
            file=d["file"],
            target=d["target"],
            category=d.get("category", DEFAULT_CATEGORY),
            inverted=d.get("inverted", False),
        )


@dataclass
class AppConfig:
    root_path: str = str(DEFAULT_ROOT_PATH)
    modules: list[ModuleEntry] = field(default_factory=list)
    theme: str = "system"
    language: str = "auto"
    load_warning: str | None = None

    @staticmethod
    def load(path: Path = DEFAULT_CONFIG_FILE) -> "AppConfig":
        if not path.exists():
            return AppConfig()

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            backup_path = path.with_suffix(path.suffix + ".corrupted")
            try:
                shutil.copy2(path, backup_path)
            except OSError:
                backup_path = None
            warning = (
                f"{path} contient du JSON invalide ({exc}). "
                f"Repartie sur une config vide."
            )
            if backup_path:
                warning += f" Ancien fichier sauvegardé en {backup_path}."
            return AppConfig(load_warning=warning)

        try:
            return AppConfig(
                root_path=raw.get("root_path", str(DEFAULT_ROOT_PATH)),
                modules=[ModuleEntry.from_dict(m) for m in raw.get("modules", [])],
                theme=raw.get("theme", "system"),
                language=raw.get("language", "auto"),
            )
        except (KeyError, ToggleError) as exc:
            return AppConfig(load_warning=f"Config invalide ({exc}). Repartie sur une config vide.")

    def save(self, path: Path = DEFAULT_CONFIG_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "root_path": self.root_path,
            "modules": [m.to_dict() for m in self.modules],
            "theme": self.theme,
            "language": self.language,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _import_line_pattern(target: str) -> re.Pattern:
    escaped = re.escape(target.strip())
    return re.compile(rf"^(?P<indent>[ \t]*)(?P<hash>#[ \t]*)?(?P<path>{escaped})[ \t]*$")


def read_import_state(file_path: Path, target: str) -> bool:
    pattern = _import_line_pattern(target)
    text = file_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            return m.group("hash") is None
    raise ToggleError(
        f"Impossible de trouver la ligne d'import '{target}' dans {file_path}"
    )


def set_import_state(file_path: Path, target: str, enabled: bool) -> None:
    pattern = _import_line_pattern(target)
    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)

    found_idx = None
    for i, raw_line in enumerate(lines):
        m = pattern.match(raw_line.rstrip("\n"))
        if m:
            found_idx = i
            break

    if found_idx is None:
        raise ToggleError(
            f"Impossible de trouver la ligne d'import '{target}' dans {file_path}"
        )

    line = lines[found_idx]
    newline = "\n" if line.endswith("\n") else ""
    stripped = line.rstrip("\n")

    m = pattern.match(stripped)
    indent = m.group("indent")
    path_part = m.group("path")

    if enabled:
        new_line = f"{indent}{path_part}{newline}"
    else:
        new_line = f"{indent}#{path_part}{newline}"

    lines[found_idx] = new_line
    _write_text_with_privilege_fallback(file_path, "".join(lines))


def _write_text_with_privilege_fallback(file_path: Path, content: str) -> None:
    try:
        file_path.write_text(content, encoding="utf-8")
        return
    except PermissionError:
        pass

    if shutil.which("pkexec") is None:
        raise ToggleError(
            f"Permission refusée pour écrire dans {file_path}, et pkexec "
            f"n'est pas disponible pour demander les droits root."
        )

    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, suffix=".nix"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["pkexec", "cp", tmp_path, str(file_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ToggleError(
                f"Échec de l'écriture élevée (pkexec) dans {file_path} : "
                f"{result.stderr.strip() or 'code ' + str(result.returncode)}"
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def resolve_path(root_path: str, relative_file: str) -> Path:
    return Path(root_path).expanduser() / relative_file


def read_state(root_path: str, entry: ModuleEntry) -> bool:
    file_path = resolve_path(root_path, entry.file)
    if file_path.is_dir():
        raise ToggleError(
            f"'{entry.file}' est un dossier, pas un fichier "
            f"(il manque probablement le nom du default.nix à la fin du chemin)."
        )
    if not file_path.is_file():
        raise ToggleError(f"Fichier introuvable : {file_path}")
    raw_state = read_import_state(file_path, entry.target)
    return (not raw_state) if entry.inverted else raw_state


def set_state(root_path: str, entry: ModuleEntry, enabled: bool) -> None:
    file_path = resolve_path(root_path, entry.file)
    if file_path.is_dir():
        raise ToggleError(
            f"'{entry.file}' est un dossier, pas un fichier "
            f"(il manque probablement le nom du default.nix à la fin du chemin)."
        )
    if not file_path.is_file():
        raise ToggleError(f"Fichier introuvable : {file_path}")

    raw_enabled = (not enabled) if entry.inverted else enabled
    set_import_state(file_path, entry.target, raw_enabled)


@dataclass
class ScanResult:
    file: str
    target: str
    enabled: bool
    suggested_name: str
    suggested_category: str
    children: list["ScanResult"] = field(default_factory=list)
    points_to_file: str | None = None
    inverted: bool = False


_CANDIDATE_LINE_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<hash>#[ \t]*)?"
    r"(?P<target>(?:\./[\w\-./]+)|(?:pkgs(?:-unstable)?\.[\w\-.]+))"
    r"[ \t]*;?[ \t]*$"
)

_WITH_PKGS_OPEN_RE = re.compile(
    r"with[ \t]+(?P<prefix>pkgs(?:-unstable)?)[ \t]*;[ \t]*\["
)

_BARE_PACKAGE_NAME_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<hash>#[ \t]*)?(?P<name>[A-Za-z_][\w\-.]*)[ \t]*$"
)

_SCAN_IGNORED_DIR_NAMES = {".git", "result", "node_modules"}

_SCAN_SYSTEM_DIR_NAMES = {
    "system",
    "services",
    "utilities",
    "configuration",
    "settings",
    "game-performance",
    "packages",
}

_SCAN_EXPLODE_DIR_NAMES = {"gnome"}

_SCAN_MAX_FILES = 500


def _scan_raw_results_by_file(root: Path) -> dict[str, list[ScanResult]]:
    by_file: dict[str, list[ScanResult]] = {}
    files_scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in _SCAN_IGNORED_DIR_NAMES
            and d.lower() not in _SCAN_SYSTEM_DIR_NAMES
        ]

        if "default.nix" not in filenames:
            continue

        files_scanned += 1
        if files_scanned > _SCAN_MAX_FILES:
            break

        file_path = Path(dirpath) / "default.nix"
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        try:
            relative_file = str(file_path.relative_to(root)).replace("\\", "/")
        except ValueError:
            continue

        file_results: list[ScanResult] = []
        inside_with_pkgs = False
        inside_inverted_block = False

        for line in text.splitlines():
            if not inside_with_pkgs:
                with_match = _WITH_PKGS_OPEN_RE.search(line)
                if with_match:
                    inside_with_pkgs = True
                    inside_inverted_block = "excludePackages" in line
                    continue

                m = _CANDIDATE_LINE_RE.match(line)
                if not m:
                    continue
                target = m.group("target")
                enabled = m.group("hash") is None

                if target.startswith("./"):
                    suggested_name = target.lstrip("./").split("/")[-1]
                    if suggested_name.lower() in _SCAN_SYSTEM_DIR_NAMES:
                        continue
                else:
                    suggested_name = target.split(".")[-1]

                file_results.append(
                    ScanResult(
                        file=relative_file,
                        target=target,
                        enabled=enabled,
                        suggested_name=suggested_name,
                        suggested_category="",
                    )
                )
            else:
                stripped = line.strip().lstrip("#").strip()
                if stripped == "]" or stripped == "];" or stripped.startswith("]"):
                    inside_with_pkgs = False
                    with_match = _WITH_PKGS_OPEN_RE.search(line)
                    if with_match:
                        inside_with_pkgs = True
                        inside_inverted_block = "excludePackages" in line
                    continue

                m = _BARE_PACKAGE_NAME_RE.match(line)
                if not m:
                    continue
                name = m.group("name")
                line_enabled = m.group("hash") is None
                enabled = (not line_enabled) if inside_inverted_block else line_enabled

                file_results.append(
                    ScanResult(
                        file=relative_file,
                        target=name,
                        enabled=enabled,
                        suggested_name=name.split(".")[-1],
                        suggested_category="",
                        inverted=inside_inverted_block,
                    )
                )

        by_file[relative_file] = file_results

    return by_file


def scan_default_nix_files(root_path: str) -> list[ScanResult]:
    root = Path(root_path).expanduser()
    if not root.is_dir():
        raise ToggleError(f"root_path introuvable ou n'est pas un dossier : {root}")

    by_file = _scan_raw_results_by_file(root)

    for source_file, results in by_file.items():
        source_dir = str(Path(source_file).parent) if Path(source_file).parent != Path(".") else ""
        for r in results:
            if not r.target.startswith("./"):
                continue
            target_subpath = r.target[2:]
            pointed_file = str(Path(source_dir) / target_subpath / "default.nix").replace("\\", "/")
            if pointed_file in by_file:
                r.points_to_file = pointed_file
                r.children = by_file[pointed_file]

    def resolve_file(file_path: str, results: list[ScanResult], last_relay_dir: str) -> list[ScanResult]:
        all_point_elsewhere = bool(results) and all(r.points_to_file for r in results)

        if all_point_elsewhere:
            own_dir = Path(file_path).parent.name or DEFAULT_CATEGORY
            resolved: list[ScanResult] = []
            for r in results:
                next_file = r.points_to_file
                next_results = by_file[next_file]
                next_all_point_elsewhere = bool(next_results) and all(
                    nr.points_to_file for nr in next_results
                )
                if next_all_point_elsewhere:
                    resolved.extend(resolve_file(next_file, next_results, own_dir))
                else:
                    if r.suggested_name.lower() in _SCAN_EXPLODE_DIR_NAMES:
                        for child in r.children:
                            child.suggested_category = r.suggested_name
                            resolved.append(child)
                    else:
                        r.suggested_category = own_dir
                        resolved.append(r)
            return resolved

        for r in results:
            r.suggested_category = last_relay_dir
        return results

    top_level: list[ScanResult] = []
    pointed_files = {
        r.points_to_file for results in by_file.values() for r in results if r.points_to_file
    }
    for file_path, results in by_file.items():
        if file_path in pointed_files:
            continue
        own_dir = Path(file_path).parent.name or DEFAULT_CATEGORY
        top_level.extend(resolve_file(file_path, results, own_dir))

    return top_level
