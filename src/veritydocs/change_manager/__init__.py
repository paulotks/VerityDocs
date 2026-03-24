"""Change Manager: pastas em docs/changes, metadata.yaml, ciclo draft → applied → archived."""

from veritydocs.change_manager.manager import (
    CreateChangeResult,
    archive_change,
    create_change,
    list_open_change_dirs,
    mark_applied,
    now_iso,
    parse_metadata_dict,
    read_metadata,
    resolve_changes_dir,
    validate_slug,
    write_metadata,
)
from veritydocs.change_manager.models import CHANGE_TYPES, ChangeMetadata, ChangeStatus

__all__ = [
    "CHANGE_TYPES",
    "ChangeMetadata",
    "ChangeStatus",
    "CreateChangeResult",
    "archive_change",
    "create_change",
    "list_open_change_dirs",
    "mark_applied",
    "now_iso",
    "parse_metadata_dict",
    "read_metadata",
    "resolve_changes_dir",
    "validate_slug",
    "write_metadata",
]
