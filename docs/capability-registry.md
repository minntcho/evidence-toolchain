# Capability Registry

The capability registry is the catalog of extraction and inspection tools that the router may choose from.

A capability is not just a function. It is a declared unit of document-processing behavior with known inputs, outputs, strengths, limits, and failure modes.

## Why a registry exists

Evidence documents are too varied for a single default parser.

The registry lets the system ask:

```text
What can we try on this document?
What does this tool require?
What does this tool produce?
What does this tool commonly get wrong?
When should this tool be followed by another tool?
```

## Capability record

A registry entry should eventually describe:

```text
name
purpose
input requirements
output shape
strengths
known limitations
failure modes
confidence semantics
fallback recommendations
review triggers
```

Example shape:

```json
{
  "name": "docling_parse",
  "purpose": "Convert structured PDFs and office documents into document structure with text, tables, layout, and reading order.",
  "input_requirements": ["pdf_or_supported_office_document"],
  "outputs": ["pages", "text_spans", "tables", "cells", "layout_blocks"],
  "strengths": ["born_digital_pdf", "tables", "reading_order"],
  "limitations": ["bad_scans", "handwriting", "cropped_photos", "domain_field_judgment"],
  "fallbacks": ["ocr_extract", "table_structure_extract", "manual_review_request"]
}
```

## Initial capability set

### `docling_parse`

Use for structured document conversion.

Good candidates:

- born-digital PDFs
- utility bills with tables
- invoices with clear text layer
- office documents
- table-heavy reports

Known limits:

- image-only scans may require OCR first
- handwriting is not a safe default
- complex tables may still need specialized table extraction
- extracted structure is not a final business judgment

### `ocr_extract`

Use for image or scan text extraction.

Good candidates:

- scanned PDFs
- receipt photos
- screenshots
- photographed invoices

Known limits:

- digits and units can be confused
- rotation, blur, glare, and crop boundaries can break extraction
- OCR text alone often loses table relationships

### `layout_kv_extract`

Use for key-value extraction where field labels and values are positioned near each other.

Good candidates:

- forms
- invoices
- receipts
- bills

Known limits:

- repeated labels can produce wrong matches
- nested table structures may confuse key-value pairing
- field names are domain-dependent

### `table_structure_extract`

Use for table reconstruction.

Good candidates:

- usage tables
- invoice line items
- meter reading logs
- monthly activity tables

Known limits:

- merged cells, multi-row headers, footnotes, and page breaks are risky
- table geometry may be right while semantic field mapping is wrong

### `receipt_extract`

Use for receipt-specific fields.

Potential fields:

- transaction date
- merchant
- item description
- quantity
- unit
- amount
- total

Known limits:

- price and physical quantity may be confused
- one receipt usually represents one transaction, not necessarily a reporting-period total
- item names may need domain mapping

### `invoice_extract`

Use for invoice-specific fields.

Potential fields:

- supplier
- invoice number
- billing period
- line item
- quantity
- unit
- amount
- currency

Known limits:

- invoice amount is not always activity amount
- billing period may differ from invoice date
- tax, fee, and subtotal rows can be misread as activity rows

### `utility_bill_extract`

Use for electricity, gas, water, steam, or similar utility bills.

Potential fields:

- customer/site name
- service address
- billing period
- meter id
- usage amount
- usage unit
- supplier

Known limits:

- bill date and service period differ
- peak/off-peak rows may need aggregation
- correction rows and estimates must be flagged

### `meter_photo_read`

Use for physical meter images.

Potential fields:

- meter id
- visible reading
- unit if visible
- timestamp if embedded or provided externally

Known limits:

- a single reading is not a period usage amount
- site-to-meter mapping is required elsewhere
- glare, angle, and display type can make values ambiguous

### `handwriting_read`

Use for handwritten logs or handwritten fields.

Potential fields:

- dates
- readings
- quantities
- names
- signatures

Known limits:

- should usually trigger review
- values require stronger provenance and often cross-checking
- overwritten or corrected values need explicit issues

### `barcode_read`

Use for barcodes or QR codes.

Potential fields:

- document id
- supplier code
- invoice/payment lookup reference
- verification URL if available

Known limits:

- code contents may require external lookup
- QR existence does not prove business value correctness

### `vision_extract`

Use when document state requires visual reasoning beyond text extraction.

Good candidates:

- screenshots
- photos
- mixed visual documents
- poor layout recovery cases

Known limits:

- should not silently replace provenance-rich extraction
- natural language answers must be grounded back to visible spans or regions where possible

### `manual_review_request`

Use when automated extraction is insufficient, ambiguous, or high-risk.

This is a capability because review is part of the toolchain, not an afterthought.

It should preserve:

- what needs review
- why review was requested
- which fields are uncertain
- which tool outputs caused the uncertainty

## Registry policy

Adding a new capability should require documenting:

1. When to use it.
2. When not to use it.
3. What output it promises.
4. What it cannot guarantee.
5. What issues it may emit.
6. What fallback or review path should follow failure.

A capability without documented limits is not ready for default routing.
