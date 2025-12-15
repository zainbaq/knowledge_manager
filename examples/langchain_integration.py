#!/usr/bin/env python3
"""LangChain integration example for Knowledge Manager API.

This example shows how to use Knowledge Manager as a retriever
in LangChain for RAG (Retrieval Augmented Generation) applications.
"""

import os
from typing import List

import requests
from langchain.schema import Document
from langchain.schema.retriever import BaseRetriever


class KnowledgeManagerRetriever(BaseRetriever):
    """LangChain-compatible retriever for Knowledge Manager."""

    base_url: str
    api_key: str
    collection: str
    k: int = 5  # Number of results to return

    def __init__(self, base_url: str, api_key: str, collection: str, k: int = 5):
        """Initialize the retriever.

        Args:
            base_url: Base URL of the Knowledge Manager API
            api_key: API key for authentication
            collection: Collection name to query
            k: Number of results to return (not currently used, but kept for compatibility)
        """
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.collection = collection
        self.k = k

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve documents for a query.

        Args:
            query: Search query text

        Returns:
            List of LangChain Document objects
        """
        response = requests.post(
            f"{self.base_url}/api/v1/query/",
            json={"query": query, "collection": self.collection},
            headers={"X-API-Key": self.api_key},
        )
        response.raise_for_status()

        data = response.json()
        context = data["context"]

        # Split context back into documents
        # (Each paragraph is treated as a separate document)
        chunks = [chunk.strip() for chunk in context.split("\n\n") if chunk.strip()]

        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "source": self.collection,
                    "retriever": "KnowledgeManager",
                },
            )
            for chunk in chunks
        ]

        return docs

    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Async version of _get_relevant_documents."""
        # For simplicity, we'll use the sync version
        # In production, you'd want to use aiohttp here
        return self._get_relevant_documents(query)


def example_basic_retrieval():
    """Example 1: Basic document retrieval."""
    print("=" * 60)
    print("Example 1: Basic Document Retrieval")
    print("=" * 60)

    retriever = KnowledgeManagerRetriever(
        base_url="http://localhost:8000",
        api_key="your-api-key-here",
        collection="documentation",
    )

    # Retrieve documents
    query = "What are the main features?"
    docs = retriever.get_relevant_documents(query)

    print(f"\nQuery: {query}")
    print(f"Retrieved {len(docs)} documents:\n")

    for i, doc in enumerate(docs, 1):
        print(f"{i}. {doc.page_content[:100]}...")
        print(f"   Source: {doc.metadata['source']}\n")


def example_rag_with_openai():
    """Example 2: RAG with OpenAI (requires langchain-openai)."""
    print("\n" + "=" * 60)
    print("Example 2: RAG with OpenAI")
    print("=" * 60)

    try:
        from langchain.chains import RetrievalQA
        from langchain_openai import ChatOpenAI

        # Initialize retriever
        retriever = KnowledgeManagerRetriever(
            base_url="http://localhost:8000",
            api_key="your-api-key-here",
            collection="documentation",
        )

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Create QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
        )

        # Run query
        query = "What are the main features of the API?"
        result = qa_chain({"query": query})

        print(f"\nQuery: {query}")
        print(f"\nAnswer: {result['result']}")
        print(f"\nSource documents: {len(result['source_documents'])}")

    except ImportError:
        print("\n⚠️  langchain-openai not installed")
        print("Install with: pip install langchain-openai")


def example_conversational_retrieval():
    """Example 3: Conversational retrieval with memory."""
    print("\n" + "=" * 60)
    print("Example 3: Conversational Retrieval")
    print("=" * 60)

    try:
        from langchain.chains import ConversationalRetrievalChain
        from langchain.memory import ConversationBufferMemory
        from langchain_openai import ChatOpenAI

        # Initialize retriever
        retriever = KnowledgeManagerRetriever(
            base_url="http://localhost:8000",
            api_key="your-api-key-here",
            collection="documentation",
        )

        # Initialize LLM and memory
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True, output_key="answer"
        )

        # Create conversational chain
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            return_source_documents=True,
        )

        # Simulate conversation
        queries = [
            "What are the main features?",
            "How do I use the upload endpoint?",
            "What about authentication?",
        ]

        for query in queries:
            result = qa_chain({"question": query})
            print(f"\nUser: {query}")
            print(f"Assistant: {result['answer']}")

    except ImportError:
        print("\n⚠️  langchain-openai not installed")
        print("Install with: pip install langchain-openai")


def example_multi_collection_retrieval():
    """Example 4: Query multiple collections."""
    print("\n" + "=" * 60)
    print("Example 4: Multi-Collection Retrieval")
    print("=" * 60)

    # For multi-collection, we can make a direct API call
    response = requests.post(
        "http://localhost:8000/api/v1/query/",
        json={
            "query": "API documentation",
            "collections": ["documentation", "tutorials", "examples"],
        },
        headers={"X-API-Key": "your-api-key-here"},
    )

    if response.status_code == 200:
        data = response.json()
        context = data["context"]
        print(f"\nContext from multiple collections:")
        print(f"{context[:300]}...")
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(f"  {response.json().get('detail', 'Unknown error')}")


def main():
    """Run all examples."""
    print("\n" + "#" * 60)
    print("# Knowledge Manager + LangChain Integration Examples")
    print("#" * 60)

    example_basic_retrieval()
    example_rag_with_openai()
    example_conversational_retrieval()
    example_multi_collection_retrieval()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"\n✗ API Error: {e}")
        if e.response is not None:
            try:
                error_detail = e.response.json().get("detail", "Unknown error")
                print(f"  Detail: {error_detail}")
            except:
                print(f"  Response: {e.response.text}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
