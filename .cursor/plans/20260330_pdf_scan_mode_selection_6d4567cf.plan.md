---
name: PDF Scan Mode Selection
overview: Add a user-driven scan mode selection flow when a PDF file is opened for the first time. The backend will signal the frontend to show a modal, the user picks a scan option, and the choice is sent back to drive the extraction pipeline.
todos:
  - id: model-update
    content: Add ScanMode enum and FileTaskScanRequired response model to app/models/file_task.py
    status: completed
  - id: endpoint-update
    content: Add scan_mode param and 202 early-return for PDF without scan_mode in open_file_task endpoint
    status: completed
  - id: bg-task-update
    content: Pass scan_mode through bg_atask_extract_file_text in file_task_extract.py
    status: completed
  - id: extractor-update
    content: Refactor extract_text_from_pdf into a scan_mode dispatcher and add _extract_text_from_pdf_google_ocr
    status: completed
  - id: config-update
    content: Add GOOGLE_CLOUD_VISION_API_KEY to app/core/config.py
    status: completed
isProject: false
---

# PDF Scan Mode Selection Plan

## Flow Diagram

```mermaid
flowchart TD
    A["Frontend: User clicks PDF file"] --> B["POST /file-tasks/open/{file_id}"]
    B --> C{Task exists in DB?}
    C -->|Yes| D["Return existing task (200)"]
    C -->|No - scan_mode missing| E["Return 202 needs_scan_mode=true"]
    E --> F["Frontend: Show scan mode modal"]
    F --> G{"User selects option"}
    G -->|"text"| H["POST /file-tasks/open/{file_id} + scan_mode=text"]
    G -->|"google_ocr"| I["POST /file-tasks/open/{file_id} + scan_mode=google_ocr"]
    G -->|"upstage_ocr"| J["POST /file-tasks/open/{file_id} + scan_mode=upstage_ocr"]
    H & I & J --> K["Create task, launch background extraction"]
    K --> L["Return task with rsmq_channel_id (200)"]
```

## Backend Changes

### 1. `[app/models/file_task.py](app/models/file_task.py)`

- Add `ScanMode` enum: `text | google_ocr | upstage_ocr`
- Add `FileTaskScanRequired` response model: `{ needs_scan_mode: true, file_id }`

### 2. `[app/api/v1/endpoints/file_task.py](app/api/v1/endpoints/file_task.py)`

- Add optional `scan_mode: ScanMode | None = None` to the `open_file_task` request body (new `OpenFileTaskRequest` schema)
- Modify Step 4b (ASYNC PATH, PDF only):
  - If `file_ext == ".pdf"` and `scan_mode is None` → return `202` with `FileTaskScanRequired`
  - If `scan_mode` is provided → proceed normally, pass `scan_mode` to background task
- All other formats (DOCX, PPTX, etc.) remain unchanged

```python
# New logic inserted before Step 4b for PDF
if category == FileCategory.PDF and scan_mode is None:
    return JSONResponse(
        status_code=202,
        content={"needs_scan_mode": True, "file_id": str(file_id)}
    )
```

### 3. `[app/api/v1/endpoints/file_task_extract.py](app/api/v1/endpoints/file_task_extract.py)`

- Add `scan_mode: str = "text"` to `bg_atask_extract_file_text` signature
- Pass `scan_mode` into the PDF extractor call

### 4. `[app/utils/utils_file_extract.py](app/utils/utils_file_extract.py)`

- Add `_extract_text_from_pdf_google_ocr(file_bytes)` using Google Cloud Vision API
- Refactor `extract_text_from_pdf` into a dispatcher:

```python
def extract_text_from_pdf(file_bytes: bytes, scan_mode: str = "text") -> str:
    if scan_mode == "google_ocr":
        return _extract_text_from_pdf_google_ocr(file_bytes)
    elif scan_mode == "upstage_ocr":
        return _extract_text_from_pdf_ocr(file_bytes)  # existing Upstage
    else:  # "text"
        return _extract_text_from_pdf_pymupdf(file_bytes)  # existing PyMuPDF
```

- Remove the auto-detection fallback logic (the `avg_chars` heuristic) - mode is now explicit

### 5. `[app/core/config.py](app/core/config.py)`

- Add `GOOGLE_CLOUD_VISION_API_KEY: str = ""` setting (Upstage key already exists)

## Scan Mode Behavior Summary

- `text` — PyMuPDF direct text layer extraction (fast, no OCR)
- `google_ocr` — Google Cloud Vision API, returns text split into blocks per image region
- `upstage_ocr` — Upstage Document Digitization API (`/v1/document-digitization`), left-to-right alignment (already implemented as `_extract_text_from_pdf_ocr`)

## Frontend (not in this repo)

- On `202` response with `needs_scan_mode: true`, show modal with 3 options
- On selection, re-call `POST /file-tasks/open/{file_id}` with `{ scan_mode: "text" | "google_ocr" | "upstage_ocr" }` in request body
- On `200`, proceed as normal (start listening to `rsmq_channel_id`)
