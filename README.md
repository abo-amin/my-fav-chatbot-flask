# Knowledge Base Chatbot 🤖

![Dashboard Screenshot](https://raw.githubusercontent.com/abo-amin/my-fav-chatbot-flask/main/screenshots/dashboard.png)

> **Enterprise-grade Document Q&A System powered by local AI (Ollama)**
> 
> *Chat with your PDFs, Word docs, and Excel sheets using strictly grounded answers.*

## ✨ Features

- **📚 Multi-Format Support**: Upload PDF, DOCX, CSV, XLSX, and TXT files.
- **🧠 Local AI Power**: Runs completely offline using **Ollama** (Llama 3, Mistral, Qwen, etc.).
- **⚡ Semantic Search**: Uses `FAISS` and `Sentence Transformers` for high-precision retrieval.
- **🎯 Strict Context Mode**: Answers questions **only** from your documents (No hallucinations).
- **🛡️ Admin Dashboard**: Full control over documents, API keys, and model settings.
- **🔌 RESTful API**: Integrate the chatbot into other apps easily.

| Dashboard | Document Management |
|-----------|---------------------|
| ![Stats](https://raw.githubusercontent.com/abo-amin/my-fav-chatbot-flask/main/screenshots/dashboard_stats.png) | ![Docs](https://raw.githubusercontent.com/abo-amin/my-fav-chatbot-flask/main/screenshots/docs.png) |

| AI Settings | Chat Interface |
|-----------|----------------|
| ![Settings](https://raw.githubusercontent.com/abo-amin/my-fav-chatbot-flask/main/screenshots/settings.png) | ![Chat](https://raw.githubusercontent.com/abo-amin/my-fav-chatbot-flask/main/screenshots/chat.png) |

---

## 🚀 Quick Start

### Prerequisites

1.  **Python 3.9+**
2.  **[Ollama](https://ollama.com/)** installed and running.

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/abo-amin/my-fav-chatbot-flask.git
cd my-fav-chatbot-flask

# 2. Install dependencies
pip install -r requirements.txt
pip install tf-keras  # Needed for some environments

# 3. Pull an AI Model (e.g., Llama 3)
ollama pull llama3
```

### Running the App

```bash
# Start the Flask server
python app.py
```

Visit **`http://localhost:5000/admin`** to log in.

> **Default Credentials:**
> *   Username: `admin`
> *   Password: `admin123`

---

## 🛠️ Configuration

You can customize the system in `config.py`:

```python
# Search Precision
SIMILARITY_THRESHOLD = 0.25  # Lower = More results, Higher = More strict
TOP_K_RESULTS = 3           # Number of chunks to use for context

# Model Settings
DEFAULT_MODEL = "llama3"
```

---

## 🔌 API Reference

Authenticate requests with header: `X-API-Key: <your-api-key>`

### `POST /api/v1/chat`

Send a question to the bot.

**Request:**
```json
{
  "question": "What are the design issues mentioned in the PDF?"
}
```

**Response:**
```json
{
  "answer": "The design issues include scalability and data synchronization...",
  "source_type": "documents",
  "from_documents": true,
  "sources": [
    {
      "content": "...",
      "score": 0.35,
      "metadata": "lecture_notes.pdf"
    }
  ]
}
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](https://choosealicense.com/licenses/mit/)
