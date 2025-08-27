import re
import uuid
from typing import List, Dict

from app.config import settings

class TextProcessor:
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
    
    def chunk_text(self, text: str, file_id: str, filename: str) -> List[Dict]:
        """Split text into overlapping chunks"""
        
        # Clean text
        text = self._clean_text(text)
        
        # Split into sentences for better chunking
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = ""
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(self._create_chunk(current_chunk, file_id, filename))
                
                # Start new chunk with overlap
                current_chunk = self._get_overlap_text(current_chunk)
                current_length = len(current_chunk)
            
            current_chunk += sentence + " "
            current_length += sentence_length + 1
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(self._create_chunk(current_chunk, file_id, filename))
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\[\]{}\'"-]', ' ', text)
        
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text for next chunk"""
        words = text.split()
        overlap_words = words[-self.chunk_overlap // 10:]  # Rough word count
        return " ".join(overlap_words)
    
    def _create_chunk(self, content: str, file_id: str, filename: str) -> Dict:
        """Create a chunk dictionary"""
        return {
            'id': str(uuid.uuid4()),
            'file_id': file_id,
            'filename': filename,
            'content': f"From file: {filename}\n\n{content.strip()}"
        }