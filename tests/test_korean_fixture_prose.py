from pathlib import Path


FIXTURE_REPLACEMENTS = {
    "Usage 6.4 MWh": "사용량 6.4 MWh",
    "Unknown evidence document": "알 수 없는 증거 문서",
    "Synthetic rotated scanned utility bill": "회전된 합성 스캔 유틸리티 청구서",
    "Diesel quantity: 42.0 L": "디젤 수량: 42.0 L",
    "Total: 62.58": "합계: 62.58",
}


def test_test_sources_use_korean_fixture_prose():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("tests").glob("test_*.py")
        if path.name != "test_korean_fixture_prose.py"
    )

    for old, new in FIXTURE_REPLACEMENTS.items():
        assert old not in source
        assert new in source


def test_synthetic_generated_documents_use_korean_sample_names(tmp_path):
    from synthetic.generator import generate_case
    from synthetic.manifests import load_manifests

    generated_text = "\n".join(
        generate_case(manifest, tmp_path / manifest.case_id).document_path.read_text(
            encoding="utf-8"
        )
        for manifest in load_manifests()
    )

    old_names = {
        "Korea Electric Utility",
        "Sample Fuel Station",
        "Internal Meter Log",
    }
    new_names = {
        "한국전력 예시",
        "샘플 주유소",
        "내부 계량기 기록",
    }

    for old_name in old_names:
        assert old_name not in generated_text
    for new_name in new_names:
        assert new_name in generated_text
