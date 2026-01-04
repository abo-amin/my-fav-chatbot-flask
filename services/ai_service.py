"""
AI Service - Handles AI response generation using Ollama
"""
from typing import Dict, Optional, List
from models import database
from services.ollama_service import ollama_service
import config


class AIService:
    """AI response generation service"""
    
    def __init__(self):
        self.ollama = ollama_service
    
    def get_model_settings(self) -> Dict:
        """Get current model settings from database"""
        return database.get_model_settings()
    
    def generate_response(self, prompt: str, context: str = None, 
                          use_context: bool = True) -> Dict:
        """Generate a response using the configured AI model"""
        settings = self.get_model_settings()
        
        # Build the full prompt
        if context and use_context:
            full_prompt = self._build_context_prompt(prompt, context)
        else:
            full_prompt = prompt
        
        # Get system prompt
        system_prompt = settings.get('system_prompt') or self._get_default_system_prompt()
        
        # Try primary model
        response = self.ollama.generate(
            prompt=full_prompt,
            model=settings.get('active_model', config.DEFAULT_MODEL),
            system_prompt=system_prompt,
            temperature=settings.get('temperature', 0.7),
            context_length=settings.get('context_length', 4096),
            top_p=settings.get('top_p', 0.9),
            top_k=settings.get('top_k', 40)
        )
        
        # If primary model fails and fallback is configured, try fallback
        if response.startswith("Error:") and settings.get('fallback_model'):
            response = self.ollama.generate(
                prompt=full_prompt,
                model=settings.get('fallback_model'),
                system_prompt=system_prompt,
                temperature=settings.get('temperature', 0.7),
                context_length=settings.get('context_length', 4096),
                top_p=settings.get('top_p', 0.9),
                top_k=settings.get('top_k', 40)
            )
            return {
                'response': response,
                'model_used': settings.get('fallback_model'),
                'used_fallback': True
            }
        
        return {
            'response': response,
            'model_used': settings.get('active_model', config.DEFAULT_MODEL),
            'used_fallback': False
        }
    
    def generate_from_documents(self, question: str, 
                                 relevant_docs: List[Dict]) -> Dict:
        """Generate response based on document context"""
        # Build context from relevant documents
        context_parts = []
        sources = []
        
        # Limit to top 3 chunks for higher precision
        for i, doc in enumerate(relevant_docs[:3]):  
            context_parts.append(f"[Section {i+1}]\n{doc['content']}")
            sources.append({
                'doc_id': doc['doc_id'],
                'chunk_index': doc['chunk_index'],
                'score': doc['score'],
                'metadata': doc['metadata']
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate response with context
        result = self.generate_response(question, context, use_context=True)
        result['sources'] = sources
        result['source_type'] = 'documents'
        
        return result
    
    def generate_from_knowledge(self, question: str) -> Dict:
        """Generate response from AI model's knowledge (no documents)"""
        prompt = f"""The user asked a question that could not be found in the uploaded documents.
Please provide the best possible answer based on your general knowledge.
Start your response by briefly noting that this information was not found in the uploaded documents.

Question: {question}

Provide a helpful, accurate, and well-structured answer:"""
        
        result = self.generate_response(prompt, use_context=False)
        result['source_type'] = 'ai_model'
        result['sources'] = []
        
        return result
    
    def refine_answer(self, answer: str, question: str) -> str:
        """Refine and improve an answer"""
        prompt = f"""Please refine and improve the following answer to make it clearer, 
more concise, and better structured. Keep the same information but improve the presentation.

Original Question: {question}

Original Answer: {answer}

Refined Answer:"""
        
        result = self.generate_response(prompt, use_context=False)
        
        # If refinement fails, return original
        if result['response'].startswith("Error:"):
            return answer
        
        return result['response']
    
    def _build_context_prompt(self, question: str, context: str) -> str:
        """Build a prompt with context"""
        return f"""You are a specialized Knowledge Base assistant. Your goal is to answer the question using ONLY the provided context snippets.

STRICT INSTRUCTIONS:
1. Use ONLY the information in the Context sections below.
2. Do NOT add outside knowledge or general assumptions.
3. Be precise and specific. Avoid general inputs.
4. If the answer is not in the context, state "I cannot find specific information about this in the provided documents."
5. Quote specific values, definitions, or steps from the text if available.

Context:
{context}

Question: {question}

Detailed Answer (based ONLY on context):"""
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt"""
        return """You are a precision-focused AI assistant for document analysis.
Your primary directive is to provide accurate answers based SOLELY on the provided document context.
Do not hallucinate or provide general knowledge unless explicitly asked when no context is available.
Focus on specific details, numbers, and facts from the text."""


# Singleton instance
ai_service = AIService()
