"""Utility functions for gathering files and reading their contents."""

from pathlib import Path
from typing import List, Union
import fitz  # PyMuPDF
import docx
from config import ALLOWED_FILE_EXTENSIONS
from logging_config import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = ALLOWED_FILE_EXTENSIONS

def collect_files_from_path(path: Union[Path, str]) -> List[Path]:
    """Return all files under *path* that match supported extensions."""
    files: List[Path] = []
    path = Path(path)
    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
        files.append(path)
    elif path.is_dir():
        for file in path.rglob("*"):
            if file.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(file)
    return files

def extract_text_from_file(path: Path) -> str:
    """Read a file from disk and return its textual content."""
    ext = path.suffix.lower()
    logger.debug(f"Extracting text from {path.name} (type: {ext})")
    try:
        if ext == ".txt" or ext == ".md":
            content = path.read_text(encoding="utf-8", errors="ignore")
            logger.debug(f"Extracted {len(content)} characters from {path.name}")
            return content

        elif ext == ".pdf":
            content = extract_text_from_pdf(path)
            logger.debug(f"Extracted {len(content)} characters from PDF {path.name}")
            return content

        elif ext == ".docx":
            content = extract_text_from_docx(path)
            logger.debug(f"Extracted {len(content)} characters from DOCX {path.name}")
            return content

        else:
            logger.warning(f"Unsupported file extension: {ext} for {path.name}")
            return ""
    except Exception as e:
        logger.error(f"Failed to read {path.name}: {e}", exc_info=True)
        return ""

def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(path: Path) -> str:
    """Extract text from a Microsoft Word document."""
    doc = docx.Document(path)
    return "\n".join([para.text for para in doc.paragraphs])
