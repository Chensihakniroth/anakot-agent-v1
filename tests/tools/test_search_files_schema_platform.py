"""search_files advertises macOS protected-folder pruning only on the host that prunes."""

import sys

import pytest

from tools.file_tools import SEARCH_FILES_SCHEMA


@pytest.mark.skipif(sys.platform != "darwin", reason="the pruning note is macOS-only")
def test_macos_schema_explains_protected_folder_pruning():
    assert "TCC-protected folders" in SEARCH_FILES_SCHEMA["description"]


@pytest.mark.skipif(sys.platform == "darwin", reason="non-macOS hosts omit the pruning note")
def test_other_hosts_schema_omits_macos_pruning():
    description = SEARCH_FILES_SCHEMA["description"]
    assert "macOS" not in description and "TCC" not in description
