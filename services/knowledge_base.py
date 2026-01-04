"""
Knowledge Base Service - Manages vector embeddings and semantic search
Uses sentence-transformers for embeddings and FAISS for vector search
"""
import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import config


class KnowledgeBase:
    """Vector-based knowledge base for semantic search"""
    
    def __init__(self):
        self.embedding_model = None
        self.index = None
        self.documents = []  # List of (doc_id, chunk_id, content, metadata)
        self.index_path = config.VECTOR_STORE_PATH / "faiss_index.bin"
        self.docs_path = config.VECTOR_STORE_PATH / "documents.pkl"
        self._load_or_create()
    
    def _get_embedding_model(self):
        """Lazy load the embedding model"""
        if self.embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
        return self.embedding_model
    
    def _load_or_create(self):
        """Load existing index or create new one"""
        config.init_directories()
        
        try:
            import faiss
            
            if self.index_path.exists() and self.docs_path.exists():
                # Load existing index
                self.index = faiss.read_index(str(self.index_path))
                with open(self.docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                print(f"Loaded existing index with {len(self.documents)} documents")
            else:
                # Create new index
                # Using L2 distance with 384 dimensions (all-MiniLM-L6-v2)
                self.index = faiss.IndexFlatL2(384)
                self.documents = []
                print("Created new FAISS index")
        except Exception as e:
            print(f"Error loading/creating index: {e}")
            import faiss
            self.index = faiss.IndexFlatL2(384)
            self.documents = []
    
    def reindex_from_database(self):
        """Rebuild the vector index from documents stored in the database"""
        from models import database
        
        # Get all chunks from database
        all_chunks = database.get_all_chunks()
        
        if not all_chunks:
            print("No documents in database to reindex")
            return 0
        
        print(f"Reindexing {len(all_chunks)} chunks from database...")
        
        model = self._get_embedding_model()
        
        # Clear current index
        import faiss
        self.index = faiss.IndexFlatL2(384)
        self.documents = []
        
        # Generate embeddings for all chunks
        texts = [chunk['content'] for chunk in all_chunks]
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        
        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
        
        # Store document metadata
        for chunk in all_chunks:
            self.documents.append({
                'doc_id': chunk['document_id'],
                'chunk_index': chunk['chunk_index'],
                'content': chunk['content'],
                'metadata': chunk.get('metadata', f"From {chunk.get('original_filename', 'document')}")
            })
        
        # Save index
        self._save()
        
        # Update successful reindexing status in database
        unique_doc_ids = set(chunk['document_id'] for chunk in all_chunks)
        print(f"Updating index status for {len(unique_doc_ids)} documents...")
        
        for doc_id in unique_doc_ids:
            # Count chunks for this doc
            doc_chunk_count = len([c for c in all_chunks if c['document_id'] == doc_id])
            database.update_document_indexed(doc_id, doc_chunk_count)
            
        print(f"Reindexed {len(self.documents)} chunks successfully!")
        return len(self.documents)
    
    def ensure_indexed(self):
        """Ensure documents are indexed - reindex if necessary"""
        if len(self.documents) == 0:
            from models import database
            # Check if database has documents
            docs = database.get_all_documents()
            if docs:
                print("Vector store empty but database has documents. Reindexing...")
                self.reindex_from_database()
    
    def add_documents(self, doc_id: str, chunks: List[Dict]) -> int:
        """Add document chunks to the knowledge base"""
        if not chunks:
            return 0
        
        model = self._get_embedding_model()
        
        # Generate embeddings for all chunks
        texts = [chunk['content'] for chunk in chunks]
        embeddings = model.encode(texts, convert_to_numpy=True)
        
        # Add to FAISS index
        self.index.add(embeddings.astype('float32'))
        
        # Store document metadata
        for i, chunk in enumerate(chunks):
            self.documents.append({
                'doc_id': doc_id,
                'chunk_index': chunk['index'],
                'content': chunk['content'],
                'metadata': chunk.get('metadata', '')
            })
        
        # Save index
        self._save()
        
        return len(chunks)
    
    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """Search for relevant documents"""
        top_k = top_k or config.TOP_K_RESULTS
        
        if len(self.documents) == 0:
            print("DEBUG: No documents in knowledge base!")
            return []
        
        model = self._get_embedding_model()
        
        # Generate query embedding
        query_embedding = model.encode([query], convert_to_numpy=True)
        
        # Search in FAISS
        k = min(top_k, len(self.documents))
        distances, indices = self.index.search(query_embedding.astype('float32'), k)
        
        # Calculate similarity scores (convert L2 distance to similarity)
        # Lower L2 distance = higher similarity
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents) and idx >= 0:
                distance = distances[0][i]
                # Better similarity calculation: 1 / (1 + distance)
                # This gives values between 0 and 1, where closer to 1 is more similar
                similarity = 1 / (1 + distance)
                
                doc = self.documents[idx]
                print(f"DEBUG: Found doc with score {similarity:.3f}, distance {distance:.3f}")
                
                # Always add results, let chat_service decide the threshold
                results.append({
                    'doc_id': doc['doc_id'],
                    'chunk_index': doc['chunk_index'],
                    'content': doc['content'],
                    'metadata': doc['metadata'],
                    'score': float(similarity),
                    'distance': float(distance)
                })
        
        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"DEBUG: Returning {len(results)} results for query: {query[:50]}...")
        return results
    
    def delete_document(self, doc_id: str) -> bool:
        """Remove all chunks for a document from the index"""
        # Find indices to remove
        indices_to_keep = []
        docs_to_keep = []
        
        for i, doc in enumerate(self.documents):
            if doc['doc_id'] != doc_id:
                indices_to_keep.append(i)
                docs_to_keep.append(doc)
        
        if len(docs_to_keep) == len(self.documents):
            return False  # Document not found
        
        # Rebuild index without the deleted document
        if docs_to_keep:
            model = self._get_embedding_model()
            texts = [doc['content'] for doc in docs_to_keep]
            embeddings = model.encode(texts, convert_to_numpy=True)
            
            import faiss
            self.index = faiss.IndexFlatL2(384)
            self.index.add(embeddings.astype('float32'))
        else:
            import faiss
            self.index = faiss.IndexFlatL2(384)
        
        self.documents = docs_to_keep
        self._save()
        
        return True
    
    def clear(self):
        """Clear the entire knowledge base"""
        import faiss
        self.index = faiss.IndexFlatL2(384)
        self.documents = []
        self._save()
    
    def _save(self):
        """Save index to disk"""
        import faiss
        config.init_directories()
        faiss.write_index(self.index, str(self.index_path))
        with open(self.docs_path, 'wb') as f:
            pickle.dump(self.documents, f)
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        return {
            'total_chunks': len(self.documents),
            'unique_documents': len(set(doc['doc_id'] for doc in self.documents)),
            'index_size': self.index.ntotal if self.index else 0
        }


# Singleton instance
knowledge_base = KnowledgeBase()
