from pathlib import Path


def test_core_package_does_not_import_synthetic_testkit():
    core_files = [
        path
        for path in Path("src/evidence_toolchain").rglob("*.py")
        if "__pycache__" not in path.parts
    ]

    assert core_files
    for path in core_files:
        source = path.read_text(encoding="utf-8")
        assert "import synthetic" not in source
        assert "from synthetic" not in source
