from fnmatch import fnmatch
from pathlib import PurePosixPath


def matches_any_pattern(name: str, patterns: list[str]) -> bool:
    """Return True when the basename of ``name`` matches at least one fnmatch pattern."""
    basename = PurePosixPath(name).name
    return any(fnmatch(basename, pattern) for pattern in patterns)


def to_posix_name(path: PurePosixPath | str) -> str:
    """Normalize an archive member name to a forward-slash posix string."""
    return PurePosixPath(path).as_posix()
