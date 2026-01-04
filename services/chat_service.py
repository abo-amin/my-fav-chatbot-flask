"""
Chat Service - Main chat logic combining knowledge base and AI
"""
from typing import Dict, Optional, List
from models import database
from services.knowledge_base import knowledge_base
from services.ai_service import ai_service
import config


class ChatService:
    """Main chat service orchestrating KB search and AI generation"""
    
    def __init__(self):
        self.kb = knowledge_base
        self.ai = ai_service
    
    def process_question(self, question: str, api_key_id: Optional[str] = None) -> Dict:
        """Process a question and generate a response"""
        # Step 1: Search knowledge base
        search_results = self.kb.search(question)
        
        print(f"DEBUG chat_service: Got {len(search_results)} results")
        if search_results:
            print(f"DEBUG chat_service: Top score = {search_results[0]['score']}")
        
        # Step 2: Determine source and generate response
        # Use a lower threshold (0.2) to be more inclusive
        MIN_SCORE = 0.2
        if search_results and search_results[0]['score'] >= MIN_SCORE:
            # Found relevant documents
            print(f"DEBUG: Using documents for answer")
            result = self.ai.generate_from_documents(question, search_results)
            source_type = 'documents'
            source_docs = [
                f"{s['metadata']} (Score: {s['score']:.2f})" 
                for s in result.get('sources', [])
            ]
        else:
            # No relevant documents found
            print(f"DEBUG: Using AI knowledge (no docs matched)")
            result = self.ai.generate_from_knowledge(question)
            source_type = 'ai_model'
            source_docs = []
        
        # Step 3: Save to chat history
        chat_id = database.add_chat_history(
            api_key_id=api_key_id,
            question=question,
            answer=result['response'],
            source_type=source_type,
            source_documents=', '.join(source_docs) if source_docs else None
        )
        
        # Step 4: Prepare response
        response = {
            'id': chat_id,
            'question': question,
            'answer': result['response'],
            'source_type': source_type,
            'model_used': result.get('model_used', ''),
            'sources': result.get('sources', []),
            'from_documents': source_type == 'documents'
        }
        
        if source_type == 'ai_model':
            response['note'] = 'This answer is from AI general knowledge, not from uploaded documents.'
        
        return response
    
    def get_chat_history(self, limit: int = 50) -> List[Dict]:
        """Get recent chat history"""
        return database.get_chat_history(limit)
    
    def get_stats(self) -> Dict:
        """Get chat statistics"""
        chat_stats = database.get_chat_stats()
        kb_stats = self.kb.get_stats()
        
        return {
            **chat_stats,
            **kb_stats
        }


# Singleton instance
chat_service = ChatService()
