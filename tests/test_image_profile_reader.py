import json
import struct


def _minimal_png_bytes(*, width: int = 120, height: int = 80, color_type: int = 2) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
        + b"\x00\x00\x00\x00"
    )


def test_image_profile_reader_creates_image_artifact_and_metadata_unit(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import ImageProfileReader

    path = tmp_path / "receipt.png"
    path.write_bytes(_minimal_png_bytes(width=120, height=80, color_type=2))
    attachment = RawAttachment.from_path(
        path,
        attachment_id="raw_image_001",
        declared_media_type="image/png",
    )

    inventory = ImageProfileReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    assert payload["route_decisions"][0]["route"] == "image"
    assert payload["artifacts"] == [
        {
            "artifact_id": "artifact_raw_image_001",
            "artifact_type": "image",
            "parent_id": "raw_image_001",
            "media_type": "image/png",
            "source_locator": {"file_name": "receipt.png"},
            "metadata": {
                "aspect_ratio": 1.5,
                "exif_orientation": None,
                "format": "PNG",
                "height": 80,
                "mode": "RGB",
                "reader": "image_profile_reader",
                "width": 120,
            },
            "issues": [],
        }
    ]
    assert payload["units"] == [
        {
            "unit_id": "unit_raw_image_001_image_profile",
            "artifact_id": "artifact_raw_image_001",
            "unit_type": "metadata",
            "producer": "image_profile_reader",
            "text": None,
            "value": {
                "aspect_ratio": 1.5,
                "exif_orientation": None,
                "format": "PNG",
                "height": 80,
                "mode": "RGB",
                "width": 120,
            },
            "bbox": None,
            "locator": {},
            "confidence": None,
            "metadata": {},
        }
    ]
    assert "atom_type" not in payload["units"][0]
    json.dumps(payload)


def test_ingest_attachment_dispatches_image_profile_route(tmp_path):
    from evidence_toolchain.file_routing import ingest_attachment
    from evidence_toolchain.ingestion import RawAttachment

    path = tmp_path / "meter.png"
    path.write_bytes(_minimal_png_bytes(width=64, height=64, color_type=6))

    inventory = ingest_attachment(
        "bundle_001",
        RawAttachment.from_path(path, attachment_id="raw_image"),
    )
    payload = inventory.to_dict()

    assert payload["route_decisions"][0]["route"] == "image"
    assert payload["artifacts"][0]["artifact_type"] == "image"
    assert payload["artifacts"][0]["metadata"]["format"] == "PNG"
    assert payload["artifacts"][0]["metadata"]["mode"] == "RGBA"
    assert payload["units"][0]["producer"] == "image_profile_reader"


def test_image_profile_reader_preserves_unreadable_profile_issue(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import ImageProfileReader

    path = tmp_path / "broken.png"
    path.write_bytes(b"not actually an image")
    attachment = RawAttachment.from_path(path, attachment_id="raw_broken_image")

    inventory = ImageProfileReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    assert payload["artifacts"][0]["metadata"]["format"] == "unknown"
    assert payload["artifacts"][0]["metadata"]["width"] is None
    assert payload["issues"][0]["code"] == "image_profile_unreadable"
    assert payload["issues"][0]["severity"] == "warning"


def test_image_profile_reader_does_not_import_ocr_vlm_or_pillow_dependencies():
    from pathlib import Path

    source = Path("src/evidence_toolchain/readers.py").read_text(encoding="utf-8")
    forbidden_imports = [
        "import PIL",
        "from PIL",
        "import cv2",
        "import pytesseract",
        "import ocrmypdf",
        "from cv2",
        "from pytesseract",
        "from ocrmypdf",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source
