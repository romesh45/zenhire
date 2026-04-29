import io
import re

import pdfplumber


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text_parts: list[str] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    raw = "\n".join(text_parts)
    # collapse runs of whitespace / blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", raw)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()

    if len(cleaned) < 100:
        raise ValueError(
            f"Could not extract sufficient text from PDF (got {len(cleaned)} chars). "
            "Ensure the PDF is not scanned or image-only."
        )

    return cleaned
