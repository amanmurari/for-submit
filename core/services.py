import os
from io import BytesIO
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq


class LLMServiceError(Exception):
    pass


class KnowledgeBaseError(Exception):
    pass


def _cohere_client():
    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        raise KnowledgeBaseError("COHERE_API_KEY is not configured. Add it to your environment to index files.")
    try:
        import cohere
    except ImportError as exc:
        raise KnowledgeBaseError("Cohere is not installed. Run: pip install -r requirements.txt") from exc
    return cohere.ClientV2(api_key=api_key)


def _embed(texts, input_type):
    try:
        response = _cohere_client().embed(
            model=os.environ.get("COHERE_EMBED_MODEL", "embed-v4.0"),
            input_type=input_type,
            texts=texts,
            embedding_types=["float"],
        )
        return response.embeddings.float
    except KnowledgeBaseError:
        raise
    except Exception as exc:
        raise KnowledgeBaseError("Cohere could not create embeddings. Check your API key and try again.") from exc


def _collection():
    """Return the persistent Chroma collection used by all projects."""
    try:
        import chromadb
    except ImportError as exc:
        raise KnowledgeBaseError("ChromaDB is not installed. Run: pip install -r requirements.txt") from exc
    chroma_path = Path(os.environ.get("CHROMA_PATH", "./chroma_data")).resolve()
    client = chromadb.PersistentClient(path=str(chroma_path))
    return client.get_or_create_collection(name="project_knowledge", metadata={"hnsw:space": "cosine"})


def _split_text(text, size=1200, overlap=200):
    text = " ".join(text.split())
    return [text[start:start + size] for start in range(0, len(text), size - overlap) if text[start:start + size].strip()]


def extract_text(filename, content):
    suffix = os.path.splitext(filename)[1].lower()
    if suffix in {".txt", ".md", ".csv", ".json", ".html", ".py"}:
        return content.decode("utf-8", errors="replace")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        except ImportError as exc:
            raise KnowledgeBaseError("PDF support requires the pypdf package.") from exc
        except Exception as exc:
            raise KnowledgeBaseError("This PDF could not be read. Try a text-based PDF.") from exc
    raise KnowledgeBaseError("Supported knowledge-base files are PDF, TXT, MD, CSV, JSON, HTML, and PY.")


def index_file(project_file, content):
    text_chunks = _split_text(extract_text(project_file.original_name, content))
    if not text_chunks:
        raise KnowledgeBaseError("No readable text was found in this file.")
    embeddings = []
    for start in range(0, len(text_chunks), 96):
        embeddings.extend(_embed(text_chunks[start:start + 96], "search_document"))
    try:
        collection = _collection()
        ids = [f"file-{project_file.id}-chunk-{index}" for index in range(len(text_chunks))]
        collection.delete(where={"file_id": str(project_file.id)})
        collection.add(
            ids=ids,
            documents=text_chunks,
            embeddings=embeddings,
            metadatas=[{"project_id": str(project_file.project_id), "file_id": str(project_file.id), "source": project_file.original_name} for _ in text_chunks],
        )
        project_file.chunk_count = len(text_chunks)
        project_file.save(update_fields=["chunk_count"])
    except KnowledgeBaseError:
        raise
    except Exception as exc:
        raise KnowledgeBaseError("ChromaDB could not store this file's embeddings. Please try again.") from exc
    return len(text_chunks)


def retrieve_project_context(project, query, limit=4):
    try:
        collection = _collection()
        if not collection.count():
            return ""
        query_embedding = _embed([query], "search_query")[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where={"project_id": str(project.id)},
            include=["documents", "metadatas"],
        )
    except KnowledgeBaseError:
        raise
    except Exception as exc:
        raise KnowledgeBaseError("ChromaDB could not search the knowledge base. Please try again.") from exc
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    if not documents:
        return ""
    return "\n\n".join(f"[Source: {metadata['source']}]\n{document}" for document, metadata in zip(documents, metadatas))


def generate_response(project, messages, selected_prompt=None, use_knowledge_base=True):
    """Generate a response with LangChain's official Groq integration."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise LLMServiceError("GROQ_API_KEY is not configured. Add it to your environment and try again.")
    instructions = project.system_prompt or "You are a helpful assistant."
    if selected_prompt:
        instructions += f"\n\nSelected saved prompt — {selected_prompt.title}:\n{selected_prompt.content}"
    latest_question = next((message.content for message in reversed(list(messages)) if message.role == "user"), "")
    if use_knowledge_base and latest_question:
        try:
            context = retrieve_project_context(project, latest_question)
        except KnowledgeBaseError:
            context = ""
        if context:
            instructions += "\n\nUse the following retrieved project documents when relevant. If they do not answer the question, say so.\n" + context
    try:
        history = [SystemMessage(content=instructions)]
        for message in messages:
            message_class = HumanMessage if message.role == "user" else AIMessage
            history.append(message_class(content=message.content))
        llm = ChatGroq(
            model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0.2,
            api_key=api_key,
            timeout=45,
        )
        text = llm.invoke(history).content
        if not text:
            raise LLMServiceError("The AI service returned an empty response.")
        return text
    except Exception as exc:
        raise LLMServiceError("The AI service could not complete that request. Please try again.") from exc
