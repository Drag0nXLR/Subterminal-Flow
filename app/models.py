from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import enum
import markdown

class VoteType(str, enum.Enum):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"

def render_markdown(text: str) -> str:
    if not text:
        return ""
    return markdown.markdown(text, extensions=['fenced_code', 'codehilite'])

class MarkdownBodyMixin:
    body = Column(Text, nullable=False)

    @property
    def body_html(self) -> str:
        return render_markdown(self.body)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    reputation = Column(Integer, default=1)
    
    questions = relationship("Question", back_populates="owner")
    answers = relationship("Answer", back_populates="owner")
    votes = relationship("Vote", back_populates="owner")

class Question(Base, MarkdownBodyMixin):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    category = Column(String, index=True, default="general")
    tags = Column(String, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    vote_score = Column(Integer, default=0)
    
    owner = relationship("User", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="question", cascade="all, delete-orphan")

class Answer(Base, MarkdownBodyMixin):
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    vote_score = Column(Integer, default=0)
    
    owner = relationship("User", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    votes = relationship("Vote", back_populates="answer", cascade="all, delete-orphan")

class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=True)
    answer_id = Column(Integer, ForeignKey("answers.id"), nullable=True)
    vote_type = Column(String(10), nullable=False)  # "upvote" or "downvote"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="votes")
    question = relationship("Question", back_populates="votes")
    answer = relationship("Answer", back_populates="votes")