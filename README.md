# 🧠 Knowledge Indexer

A local knowledge management solution built with **FastAPI** and **Streamlit** that lets users upload files (PDF, DOCX, TXT, etc.), chunk and embed them using OpenAI embeddings, store them in a persistent **local vector database (ChromaDB)**, and query them intelligently.

---

## 🚀 Features

- ✅ Upload documents via drag-and-drop
- ✅ Automatically chunk and embed content
- ✅ Store embeddings locally using ChromaDB
- ✅ Create and update custom indexes (collections)
- ✅ Query indexed knowledge and retrieve context
- ✅ View all collections and their metadata
- ✅ Delete collections safely from the UI
- ✅ Full Python backend & frontend integration

---

## 📁 Project Structure

```
.
├── api/                     # FastAPI backend
│   └── app.py
├── ingestion/              # File collection & chunking
│   ├── file_loader.py
│   └── chunker.py
├── vector_store/           # Embedding + ChromaDB logic
│   ├── embedder.py
│   └── vector_index.py
├── streamlit_app.py        # Streamlit frontend
├── run_app.py              # Starts backend + frontend together
├── requirements.txt
└── README.md
```

---

## ⚙️ Requirements

- Python 3.9+
- OpenAI API Key (for embeddings)

### 🔧 Install dependencies

```bash
pip install -r requirements.txt
```

> Create a `.env` file with your OpenAI key:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

---

## 🧠 Embeddings & Vector Store

- Embedding model: `text-embedding-3-small` from OpenAI
- Vector DB: [ChromaDB](https://www.trychroma.com/)
- Chunking: Simple text splitter with paragraph or sentence breaks

---

## ▶️ Run the App

To launch both the backend and frontend:

```bash
python run_app.py
```

Then open:
- FastAPI backend: http://127.0.0.1:8000/docs
- Streamlit UI: http://localhost:8501

---

## 🧪 API Endpoints

| Method | Endpoint                  | Description                      |
|--------|---------------------------|----------------------------------|
| POST   | `/create-index/`          | Upload files and create index   |
| POST   | `/update-index/`          | Add files to existing index     |
| POST   | `/query/`                 | Ask questions about an index    |
| GET    | `/list-indexes/`          | View collections and metadata   |
| DELETE | `/delete-index/{name}`    | Delete a collection             |

---

## 📌 Roadmap Ideas

- [ ] Full file preview in UI
- [ ] Multi-index search
- [ ] Support for local embedding models (offline mode)
- [ ] User authentication
- [ ] Export/Import indexes

---

## 🧑‍💻 Built With

- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://streamlit.io/)
- [ChromaDB](https://www.trychroma.com/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

---

## 📝 License

MIT License – use freely, build something awesome.
