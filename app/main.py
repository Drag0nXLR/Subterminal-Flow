from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from contextlib import asynccontextmanager
from passlib.context import CryptContext
from datetime import datetime, timedelta
import markdown
from jose import jwt
from jose.exceptions import JWTError
import uuid
from pathlib import Path
from fastapi import UploadFile, File

from . import models, schemas
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

def render_markdown(text: str) -> str:
    return markdown.markdown(text, extensions=['fenced_code', 'codehilite'])

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
    with open("templates/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/register/")
async def register_page(request: Request):
    with open("templates/register.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

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
async def create_question(question: schemas.QuestionCreate, db: AsyncSession = Depends(get_db)):
    db_question = models.Question(**question.model_dump())
    db.add(db_question)
    await db.commit()
    await db.refresh(db_question)
    await update_search_cache(db)
    return db_question

@app.get("/questions/", response_model=List[schemas.Question])
async def get_questions(skip: int = 0, limit: int = 50, category: str = None, db: AsyncSession = Depends(get_db)):
    query = select(models.Question)
    if category:
        query = query.where(models.Question.category == category)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@app.get("/questions/{question_id}", response_model=schemas.Question)
async def get_question(question_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Question).where(models.Question.id == question_id))
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