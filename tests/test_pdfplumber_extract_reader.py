import json


def _minimal_text_pdf_bytes(text: str = "usage 6.4 MWh") -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(body)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(content)


def test_pdfplumber_extract_reader_creates_text_span_and_word_box_units(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import PdfPlumberExtractReader

    path = tmp_path / "bill.pdf"
    path.write_bytes(_minimal_text_pdf_bytes())
    attachment = RawAttachment.from_path(
        path,
        attachment_id="raw_pdf_text",
        declared_media_type="application/pdf",
    )

    inventory = PdfPlumberExtractReader().read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    assert payload["artifacts"][0]["artifact_type"] == "file"
    assert payload["artifacts"][1]["artifact_type"] == "pdf_page"
    assert payload["artifacts"][1]["metadata"]["reader"] == "pdfplumber_extract"
    assert payload["artifacts"][1]["metadata"]["width"] == 612
    assert payload["artifacts"][1]["metadata"]["height"] == 792

    text_units = [unit for unit in payload["units"] if unit["unit_type"] == "text_span"]
    word_units = [unit for unit in payload["units"] if unit["unit_type"] == "word_box"]

    assert [unit["text"] for unit in text_units] == ["usage 6.4 MWh"]
    assert text_units[0]["locator"] == {"page": 1}
    assert text_units[0]["producer"] == "pdfplumber_extract"
    assert [unit["text"] for unit in word_units] == ["usage", "6.4", "MWh"]
    assert word_units[0]["locator"] == {"page": 1, "word_index": 1}
    assert len(word_units[0]["bbox"]) == 4
    assert word_units[0]["metadata"]["source_keys"] == [
        "bottom",
        "direction",
        "doctop",
        "text",
        "top",
        "upright",
        "x0",
        "x1",
    ]
    assert "atom_type" not in text_units[0]
    assert "atom_type" not in word_units[0]
    assert payload["issues"] == []
    json.dumps(payload)


def test_pdfplumber_extract_reader_preserves_missing_dependency_issue(tmp_path):
    from evidence_toolchain.file_routing import FileKindRouter, SafetyPolicy
    from evidence_toolchain.ingestion import RawAttachment
    from evidence_toolchain.readers import PdfPlumberExtractReader

    path = tmp_path / "bill.pdf"
    path.write_bytes(_minimal_text_pdf_bytes())
    attachment = RawAttachment.from_path(path, attachment_id="raw_pdf_text")

    inventory = PdfPlumberExtractReader(pdfplumber_module=None).read(
        bundle_id="bundle_001",
        attachment=attachment,
        route_decision=FileKindRouter().route(attachment),
        safety_decision=SafetyPolicy().evaluate(attachment),
    )
    payload = inventory.to_dict()

    assert payload["artifacts"][0]["artifact_type"] == "file"
    assert payload["units"] == []
    assert payload["issues"][0]["code"] == "pdfplumber_dependency_missing"
    assert payload["issues"][0]["severity"] == "blocking"
