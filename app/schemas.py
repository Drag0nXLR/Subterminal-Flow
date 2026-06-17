from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Question schemas
class QuestionBase(BaseModel):
    title: str
    body: str
    category: str = "general"
    tags: str = ""

class QuestionCreate(QuestionBase):
    pass

class Question(QuestionBase):
    id: int
    created_at: datetime
    owner_id: Optional[int] = None

    class Config:
        from_attributes = True

# Answer schemas
class AnswerBase(BaseModel):
    body: str
    question_id: int

class AnswerCreate(AnswerBase):
    pass

class Answer(AnswerBase):
    id: int
    is_accepted: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Search
class SearchQuery(BaseModel):
    query: str
    top_k: int = 5
    category: Optional[str] = None

class SearchResult(Question):
    similarity_score: float
    created_at: Optional[datetime] = None

# Categories
CATEGORIES = {
    "general": "General Discussion",
    "python": "Python",
    "javascript": "JavaScript / TypeScript",
    "web": "Web Development",
    "backend": "Backend Development",
    "frontend": "Frontend Development",
    "database": "Databases (SQL/NoSQL)",
    "ai_ml": "AI & Machine Learning",
    "devops": "DevOps & Tools",
    "algorithms": "Algorithms & Data Structures",
    "debugging": "Debugging & Testing",
    "api": "API Development",
    "other": "Other"
}

# Popular tags
POPULAR_TAGS = [
    'python', 'javascript', 'typescript', 'react', 'vue', 'angular', 
    'node.js', 'express', 'django', 'fastapi', 'flask', 'sql', 
    'postgresql', 'mongodb', 'mysql', 'api', 'rest', 'graphql', 
    'docker', 'kubernetes', 'aws', 'azure', 'git', 'linux', 
    'machine-learning', 'ai', 'deep-learning', 'tensorflow', 'pytorch', 
    'algorithms', 'data-structures', 'web', 'frontend', 'backend', 
    'fullstack', 'devops', 'testing', 'debugging', 'html', 'css'
]