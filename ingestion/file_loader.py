from pathlib import Path
import fitz  # PyMuPDF
import docx

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

def collect_files_from_path(path):
    files = []
    path = Path(path)
    if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
        files.append(path)
    elif path.is_dir():
        for file in path.rglob("*"):
            if file.suffix in SUPPORTED_EXTENSIONS:
                files.append(file)
    return files

def extract_text_from_file(path):
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
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(path):
    doc = docx.Document(path)
    return "\n".join([para.text for para in doc.paragraphs])
