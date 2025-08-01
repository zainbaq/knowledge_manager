"""Utility functions for gathering files and reading their contents."""

from pathlib import Path
import fitz  # PyMuPDF
import docx
from config import ALLOWED_FILE_EXTENSIONS

SUPPORTED_EXTENSIONS = ALLOWED_FILE_EXTENSIONS

def collect_files_from_path(path):
    """Return all files under *path* that match supported extensions."""
    files = []
    path = Path(path)
    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
        files.append(path)
    elif path.is_dir():
        for file in path.rglob("*"):
            if file.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(file)
    return files

def extract_text_from_file(path):
    """Read a file from disk and return its textual content."""
    ext = path.suffix.lower()
    try:
        if ext == ".txt" or ext == ".md":
            return path.read_text(encoding="utf-8", errors="ignore")

        elif ext == ".pdf":
            return extract_text_from_pdf(path)

        elif ext == ".docx":
            return extract_text_from_docx(path)

        else:
            return ""
    except Exception as e:
        print(f"Failed to read {path.name}: {e}")
        return ""

def extract_text_from_pdf(path):
    """Extract text from a PDF file using PyMuPDF."""
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(path):
    """Extract text from a Microsoft Word document."""
    doc = docx.Document(path)
    return "\n".join([para.text for para in doc.paragraphs])
