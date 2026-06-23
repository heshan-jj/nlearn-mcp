import io
import logging

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)


def _extract_table_text(table: Table) -> str:
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def parse_docx_content(docx_bytes: bytes) -> str:
    """
    Extract text from a DOCX file, including paragraphs and table contents.
    """
    try:
        doc = Document(io.BytesIO(docx_bytes))
        parts: list[str] = []

        for block in doc.element.body:
            tag = block.tag.split("}")[-1] if "}" in block.tag else block.tag

            if tag == "p":
                para = Paragraph(block, doc)
                text = para.text.strip()
                if text:
                    parts.append(text)
            elif tag == "tbl":
                table = Table(block, doc)
                table_text = _extract_table_text(table)
                if table_text.strip():
                    parts.append(table_text)

        return "\n\n".join(parts)
    except Exception as e:
        logger.error("Error extracting DOCX: %s", e)
        return f"Error extracting text from DOCX: {e}"
