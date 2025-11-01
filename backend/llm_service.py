from groq import Groq
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

load_dotenv()

class LLMService:
    def __init__(self, use_local_model: bool = False, local_model_path: str = None):
        """
        Initialize LLM Service with support for both Groq and local models
        
        Args:
            use_local_model: If True, uses local fine-tuned model
            local_model_path: Path to your trained model (e.g., "./trained_model/final_model")
        """
        self.use_local_model = use_local_model
        
        if use_local_model:
            self._init_local_model(local_model_path)
        else:
            self._init_groq()
    
    def _init_groq(self):
        """Initialize Groq client"""
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.1-8b-instant"
        print("✓ Using Groq API")
    
    def _init_local_model(self, model_path: str):
        """Initialize local fine-tuned model"""
        if not model_path:
            model_path = os.getenv("LOCAL_MODEL_PATH", "./trained_model/final_model")
        
        if not os.path.exists(model_path):
            raise ValueError(f"Local model not found at {model_path}")
        
        print(f"Loading local model from {model_path}...")
        
        # Detect device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.local_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map=self.device
        )
        
        # Create pipeline for easy inference
        self.generator = pipeline(
            "text-generation",
            model=self.local_model,
            tokenizer=self.tokenizer,
            device=0 if self.device == "cuda" else -1
        )
        
        print(f"✓ Local model loaded on {self.device}")
    
    def generate_response(
        self, 
        query: str, 
        context: str = None,
        chat_history: List[Dict] = None
    ) -> str:
        """Generate response using either Groq or local model"""
        
        if self.use_local_model:
            return self._generate_local(query, context, chat_history)
        else:
            return self._generate_groq(query, context, chat_history)
    
    def _generate_groq(
        self, 
        query: str, 
        context: str = None,
        chat_history: List[Dict] = None
    ) -> str:
        """Generate response using Groq"""
        
        messages = []
        
        system_prompt = """
            You are RizviGPT, an AI assistant with deep knowledge about the Rizvi College Of Engineering.
            You have access to college documents, course materials, policies, and procedures.
            Answer questions accurately based on the provided context. If you don't have enough information, say so.
            Be helpful, concise, and student-friendly. Be very flexible and elaborate on your answers and do not just retrieve data from the context.
        """
        
        if context:
            system_prompt += f"\n\nRelevant context from college documents:\n{context}"
            
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        if chat_history:
            for msg in chat_history[-5:]:
                messages.append(msg)
        
        messages.append({
            "role": "user",
            "content": query
        })
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        
        return response.choices[0].message.content
    
    def _generate_local(
        self, 
        query: str, 
        context: str = None,
        chat_history: List[Dict] = None
    ) -> str:
        """Generate response using local fine-tuned model"""
        
        # Build prompt
        prompt = self._build_local_prompt(query, context, chat_history)
        
        # Generate response
        outputs = self.generator(
            prompt,
            max_length=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id,
            truncation=True,
            num_return_sequences=1
        )
        
        # Extract generated text (remove prompt)
        generated_text = outputs[0]['generated_text']
        response = generated_text[len(prompt):].strip()
        
        # Clean up response
        response = self._clean_response(response)
        
        return response
    
    def _build_local_prompt(
        self, 
        query: str, 
        context: str = None, 
        chat_history: List[Dict] = None
    ) -> str:
        """Build prompt for local model"""
        
        prompt_parts = []
        
        # Add context if available
        if context:
            prompt_parts.append("Context from college documents:")
            prompt_parts.append(context)
            prompt_parts.append("")
        
        # Add chat history
        if chat_history:
            for msg in chat_history[-3:]:  # Last 3 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    prompt_parts.append(f"Question: {content}")
                else:
                    prompt_parts.append(f"Answer: {content}")
        
        # Add current query
        prompt_parts.append(f"Question: {query}")
        prompt_parts.append("Answer:")
        
        return "\n".join(prompt_parts)
    
    def _clean_response(self, response: str) -> str:
        """Clean up generated response"""
        
        # Remove everything after first question if model continues
        if "Question:" in response:
            response = response.split("Question:")[0]
        
        # Remove common artifacts
        response = response.replace("Answer:", "").strip()
        
        # Take only first paragraph if too long
        paragraphs = response.split("\n\n")
        if len(paragraphs) > 1 and len(response) > 500:
            response = paragraphs[0]
        
        return response.strip()
    
    def generate_streaming_response(
        self, 
        query: str, 
        context: str = None,
        chat_history: List[Dict] = None
    ):
        """Generate streaming response"""
        
        if self.use_local_model:
            # Local models don't stream well, return chunks
            response = self._generate_local(query, context, chat_history)
            
            # Simulate streaming by yielding word by word
            words = response.split()
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
        else:
            # Use Groq streaming
            yield from self._stream_groq(query, context, chat_history)
    
    def _stream_groq(
        self, 
        query: str, 
        context: str = None,
        chat_history: List[Dict] = None
    ):
        """Stream response from Groq"""
        
        messages = []
        
        system_prompt = """
            You are RizviGPT, an AI assistant with deep knowledge about the Rizvi College Of Engineering.
            You have access to college documents, course materials, policies, and procedures.
            Answer questions accurately based on the provided context. If you don't have enough information, say so.
            Be helpful, concise, and student-friendly.
        """
        
        if context:
            system_prompt += f"\n\nRelevant context from college documents:\n{context}"
            
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        if chat_history:
            for msg in chat_history[-5:]:
                messages.append(msg)
        
        messages.append({
            "role": "user",
            "content": query
        })
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# Factory function to create the right service
def create_llm_service() -> LLMService:
    """
    Create LLM service based on environment configuration
    """
    use_local = os.getenv("USE_LOCAL_MODEL", "false").lower() == "true"
    local_model_path = os.getenv("LOCAL_MODEL_PATH", "./trained_model/final_model")
    
    try:
        return LLMService(
            use_local_model=use_local,
            local_model_path=local_model_path if use_local else None
        )
    except Exception as e:
        print(f"Error initializing local model: {e}")
        print("Falling back to Groq...")
        return LLMService(use_local_model=False)