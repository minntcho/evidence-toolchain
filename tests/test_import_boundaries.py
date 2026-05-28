from pathlib import Path
import tomllib


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


def test_pdfplumber_is_optional_pdf_extra_not_required_core_dependency():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert "pdfplumber>=0.11" not in pyproject["project"].get("dependencies", [])
    assert pyproject["project"]["optional-dependencies"]["pdf"] == [
        "pdfplumber>=0.11"
    ]
