from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
from contextlib import asynccontextmanager
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from jose.exceptions import JWTError
import uuid
from pathlib import Path
from fastapi import UploadFile, File

from . import models, schemas
from .schemas import Answer, AnswerCreate, VoteCreate
from .database import engine, get_db, Base
from .ai_search import search_engine

from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(['html', 'xml']),
)

def render_template(name: str, context: dict) -> HTMLResponse:
    template = env.get_template(name)
    content = template.render(**context)
    return HTMLResponse(content=content)

SECRET_KEY = "your-secret-key-change-this-in-production-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(title="Subterminal Flow API", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        result = await db.execute(select(models.User).where(models.User.username == username))
        return result.scalar_one_or_none()
    except JWTError:
        return None

async def update_search_cache(db: AsyncSession):
    result = await db.execute(select(models.Question))
    questions = result.scalars().all()
    questions_dict = [
        {
            "id": q.id, 
            "title": q.title, 
            "body": q.body, 
            "category": q.category or "general",
            "tags": q.tags or "",
            "created_at": q.created_at.isoformat() if q.created_at else None
        } 
        for q in questions
    ]
    search_engine.update_cache(questions_dict)

# Main page
@app.get("/")
async def read_root(request: Request):
    return render_template("index.html", {"request": request})

# Image upload
@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        return JSONResponse(status_code=400, content={"error": "File must be an image"})
    
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"error": "File must be less than 2MB"})
    
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    image_url = f"/static/uploads/{unique_filename}"
    return {"url": image_url, "filename": file.filename}

# Authentication endpoints
@app.post("/register/")
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(
        (models.User.username == user.username) | (models.User.email == user.email)
    ))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password)
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    access_token = create_access_token(data={"sub": db_user.username})
    
    response = JSONResponse(
        content={"message": "Registration successful", "user_id": db_user.id},
        status_code=201
    )
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.post("/login/")
async def login(credentials: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.username == credentials.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    
    response = JSONResponse(
        content={"message": "Login successful", "username": user.username},
        status_code=200
    )
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/login/")
async def login_page(request: Request):
    return render_template("login.html", {"request": request})

@app.get("/register/")
async def register_page(request: Request):
    return render_template("register.html", {"request": request})

@app.get("/logout/")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

@app.get("/api/me")
async def get_current_user_info(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "reputation": 1
    }

@app.get("/settings/")
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    if not current_user:
        return RedirectResponse(url="/")
    return render_template("settings.html", {"request": request, "user": current_user})

@app.put("/user/")
async def update_user(
    user_update: schemas.UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user_update.username:
        current_user.username = user_update.username
    if user_update.email:
        current_user.email = user_update.email
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
    
    await db.commit()
    await db.refresh(current_user)
    
    return {"message": "Profile updated successfully"}

@app.get("/user/profile/{user_id}", response_model=schemas.User)
async def get_user_profile(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Tags page
@app.get("/tags/")
async def tags_page(request: Request):
    return render_template("tags.html", {"request": request})

@app.get("/api/tags")
async def get_tags():
    return {"tags": schemas.POPULAR_TAGS}

# Question endpoints
@app.post("/questions/", response_model=schemas.Question)
async def create_question(question: schemas.QuestionCreate, request: Request, db: AsyncSession = Depends(get_db)):
    current_user = await get_current_user(request, db)
    
    db_question = models.Question(
        **question.model_dump(),
        owner_id=current_user.id if current_user else None
    )
    db.add(db_question)
    await db.commit()
    await db.refresh(db_question)
    
    # Завантажуємо owner
    result = await db.execute(
        select(models.Question)
        .options(selectinload(models.Question.owner))
        .where(models.Question.id == db_question.id)
    )
    question_with_owner = result.scalar_one()
    
    await update_search_cache(db)
    return question_with_owner

@app.get("/questions/", response_model=List[schemas.Question])
async def get_questions(skip: int = 0, limit: int = 50, category: str = None, db: AsyncSession = Depends(get_db)):
    query = select(models.Question).options(selectinload(models.Question.owner))
    if category:
        query = query.where(models.Question.category == category)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@app.get("/questions/{question_id}", response_model=schemas.Question)
async def get_question(question_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Question)
        .options(selectinload(models.Question.owner))
        .where(models.Question.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@app.get("/questions/{question_id}/related", response_model=List[schemas.SearchResult])
async def get_related_questions(question_id: int, top_k: int = 3, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Question).where(models.Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    await update_search_cache(db)
    related = await search_engine.find_related(question_id=question_id, top_k=top_k)
    return related

@app.post("/search/", response_model=List[schemas.SearchResult])
async def search_questions(search_query: schemas.SearchQuery, db: AsyncSession = Depends(get_db)):
    await update_search_cache(db)
    results = await search_engine.search(
        query=search_query.query,
        top_k=search_query.top_k,
        tags=search_query.category
    )
    return results

@app.get("/categories")
async def get_categories():
    return schemas.CATEGORIES

@app.get("/api")
async def api_root():
    return {"message": "API is alive"}

# Vote endpoints
@app.post("/questions/{question_id}/vote")
async def vote_question(
    question_id: int,
    vote_data: VoteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    question = await db.get(models.Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    existing_vote = await db.execute(
        select(models.Vote).where(
            (models.Vote.user_id == current_user.id) & 
            (models.Vote.question_id == question_id)
        )
    )
    existing_vote = existing_vote.scalar_one_or_none()
    
    if existing_vote:
        if existing_vote.vote_type == vote_data.vote_type.value:
            await db.delete(existing_vote)
            question.vote_score += 1 if vote_data.vote_type.value == "downvote" else -1
        else:
            existing_vote.vote_type = vote_data.vote_type.value
            question.vote_score += 2 if vote_data.vote_type.value == "upvote" else -2
    else:
        new_vote = models.Vote(
            user_id=current_user.id,
            question_id=question_id,
            vote_type=vote_data.vote_type.value
        )
        db.add(new_vote)
        question.vote_score += 1 if vote_data.vote_type.value == "upvote" else -1
    
    await db.commit()
    await db.refresh(question)
    
    return {"vote_score": question.vote_score}

@app.post("/answers/{answer_id}/vote")
async def vote_answer(
    answer_id: int,
    vote_data: VoteCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    answer = await db.get(models.Answer, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    existing_vote = await db.execute(
        select(models.Vote).where(
            (models.Vote.user_id == current_user.id) & 
            (models.Vote.answer_id == answer_id)
        )
    )
    existing_vote = existing_vote.scalar_one_or_none()
    
    if existing_vote:
        if existing_vote.vote_type == vote_data.vote_type.value:
            await db.delete(existing_vote)
            answer.vote_score += 1 if vote_data.vote_type.value == "downvote" else -1
        else:
            existing_vote.vote_type = vote_data.vote_type.value
            answer.vote_score += 2 if vote_data.vote_type.value == "upvote" else -2
    else:
        new_vote = models.Vote(
            user_id=current_user.id,
            answer_id=answer_id,
            vote_type=vote_data.vote_type.value
        )
        db.add(new_vote)
        answer.vote_score += 1 if vote_data.vote_type.value == "upvote" else -1
    
    await db.commit()
    await db.refresh(answer)
    
    return {"vote_score": answer.vote_score}

# Answer endpoints
@app.post("/questions/{question_id}/answers", response_model=Answer)
async def create_answer(
    question_id: int,
    answer: AnswerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    question = await db.get(models.Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    db_answer = models.Answer(
        body=answer.body,
        question_id=question_id,
        owner_id=current_user.id
    )
    db.add(db_answer)
    await db.commit()
    
    # Завантажуємо з owner
    result = await db.execute(
        select(models.Answer)
        .options(selectinload(models.Answer.owner))
        .where(models.Answer.id == db_answer.id)
    )
    answer_with_owner = result.scalar_one()
    
    return answer_with_owner

@app.get("/questions/{question_id}/answers", response_model=List[Answer])
async def get_answers(question_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.Answer)
        .options(selectinload(models.Answer.owner))
        .where(models.Answer.question_id == question_id)
        .order_by(models.Answer.is_accepted.desc(), models.Answer.vote_score.desc(), models.Answer.created_at)
    )
    answers = result.scalars().all()
    return list(answers)

@app.put("/answers/{answer_id}/accept")
async def accept_answer(
    answer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    answer = await db.get(models.Answer, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    question = await db.get(models.Question, answer.question_id)
    if question.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the question owner can accept an answer")
    
    await db.execute(
        update(models.Answer)
        .where(models.Answer.question_id == question.id)
        .values(is_accepted=False)
    )
    
    answer.is_accepted = True
    await db.commit()
    await db.refresh(answer)
    
    return {"message": "Answer accepted", "answer_id": answer_id}

@app.delete("/answers/{answer_id}")
async def delete_answer(
    answer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    answer = await db.get(models.Answer, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    
    if answer.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.delete(answer)
    await db.commit()
    
    return {"message": "Answer deleted"}