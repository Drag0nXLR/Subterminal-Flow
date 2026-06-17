from sentence_transformers import SentenceTransformer, util
import torch
from typing import List, Dict

class SubterminalSearch:
    def __init__(self):
        print("🤖 Завантажую AI модель...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.questions_cache = []
        self.embeddings_cache = None
        print("✅ AI модель готова!")
    
    def update_cache(self, questions: List[Dict]):
        self.questions_cache = questions
        
        texts = []
        for q in questions:
            tags_text = f"Tags: {q.get('tags', '')}" if q.get('tags') else ""
            full_text = f"{q['title']} {q['body']} {tags_text}"
            texts.append(full_text)
        
        if texts:
            self.embeddings_cache = self.model.encode(
                texts, 
                convert_to_tensor=True,
                show_progress_bar=False
            )
        else:
            self.embeddings_cache = None
    
    async def search(self, query: str, top_k: int = 5, tags: str = None) -> List[Dict]:
        if not self.questions_cache or self.embeddings_cache is None:
            return []
        
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        cos_scores = util.cos_sim(query_embedding, self.embeddings_cache)[0]
        
        if tags:
            tag_list = [t.strip().lower() for t in tags.split(',')]
            filtered_indices = []
            filtered_scores = []
            
            for idx, question in enumerate(self.questions_cache):
                question_tags = [t.strip().lower() for t in question.get('tags', '').split(',')]
                if any(tag in question_tags for tag in tag_list):
                    filtered_indices.append(idx)
                    filtered_scores.append(cos_scores[idx].item())
            
            if not filtered_indices:
                return []
            
            sorted_pairs = sorted(
                zip(filtered_indices, filtered_scores),
                key=lambda x: x[1],
                reverse=True
            )[:top_k]
            
            results = []
            for idx, score in sorted_pairs:
                if score > 0.2:
                    question = self.questions_cache[idx].copy()
                    question['similarity_score'] = score
                    results.append(question)
            
            return results
        
        top_results = torch.topk(cos_scores, k=min(top_k, len(cos_scores)))
        
        results = []
        for score, idx in zip(top_results.values, top_results.indices):
            if score > 0.2:
                question = self.questions_cache[idx].copy()
                question['similarity_score'] = float(score)
                results.append(question)
        
        return results
    
    async def find_related(self, question_id: int, top_k: int = 3) -> List[Dict]:
        current_question = None
        for q in self.questions_cache:
            if q['id'] == question_id:
                current_question = q
                break
        
        if not current_question:
            return []
        
        tags_text = f"Tags: {current_question.get('tags', '')}" if current_question.get('tags') else ""
        query = f"{current_question['title']} {current_question['body']} {tags_text}"
        
        results = await self.search(query, top_k=top_k * 2)
        related = [q for q in results if q['id'] != question_id][:top_k]
        
        return related

search_engine = SubterminalSearch()