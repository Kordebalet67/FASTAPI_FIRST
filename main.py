import shutil
import uuid
import pandas as pd
from datetime import datetime, timedelta
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import os
import csv
import hashlib
from pathlib import Path
from PIL import Image



# Подключение всех статических файлов, шаблонов,
# инициализация веб-приложения, описание глобальных
# переменных
app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/sources", StaticFiles(directory="sources"), name="sources")
templates = Jinja2Templates(directory="templates")
USERS = "users.csv"
SESSION_TTL = timedelta(3)
sessions = {}
white_urls = ["/", "/login", "/logout", "/register"]

# Фейковый админ
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "1234"
ADMIN_PASSWORD_HASHED = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
ADMIN_AVATAR_PATH = "sources/pun.png"

# Проверяем, есть ли CSV, если нет — создаём
if not os.path.exists(USERS):
    with open(USERS, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "password_hash", "avatar_path"])
        writer.writerow([ADMIN_LOGIN, ADMIN_PASSWORD_HASHED, ADMIN_AVATAR_PATH])


# --- Хэширование через SHA-256 ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def save_user(username: str, password: str, avatar_path: str):
    """Сохраняем пользователя в CSV"""
    password_hash = hash_password(password)
    with open(USERS, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([username, password_hash, avatar_path])


def load_users():
    """Загружаем всех пользователей из CSV"""
    users = {}
    with open(USERS, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users[row["username"]] = {
                "username": row["username"],
                "password_hash": row["password_hash"],
                "avatar": row["avatar_path"]
            }
    return users


# Контроль авторизации и сессии
@app.middleware("http")
async def check_session(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path.startswith("/sources") or request.url.path in white_urls:
        return await call_next(request)

    session_id = request.cookies.get("session_id")
    if session_id not in sessions:
        return RedirectResponse(url="/")

    created_session = sessions[session_id]
    if datetime.now() - created_session > SESSION_TTL:
        del sessions[session_id]
        return templates.TemplateResponse("login.html", {"request": request, 
                                        "message": "Сессия завершена по истечении тайм-аута"})
    
    return await call_next(request)

# Автообновление сессии
def refresh_session(request: Request):
    session_id = request.cookies.get("session_id")
    created_session = sessions[session_id]
    if datetime.now() - created_session <= SESSION_TTL:
        sessions[session_id] = datetime.now()

# Маршрутизация приложения
@app.get("/", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        print(session_id)
        del sessions[session_id]
        # return RedirectResponse(url="/")
        return templates.TemplateResponse("login.html", {"request": request, 
                                        "message": "Сессия завершена из-за действия пользователя"})
    except:
        return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, 
          username: str = Form(...), 
          password: str = Form(...)):
    users = pd.read_csv(USERS)
    print(users)
    print(username)
    print(users['username'].values)
    if username in users['username'].values:
        if verify_password(password, str(users[users["username"] == username].values[0][1])): # str(users[users["username"] == username].values[0][1]) == password:
            session_id = str(uuid.uuid4())
            sessions[session_id] = datetime.now()
            response = RedirectResponse(url=f"/home/{username}", status_code=302)
            response.set_cookie(key="session_id", value=session_id)
            return response
        return templates.TemplateResponse("login.html",
                                       {"request": request, 
                                        "error": "Неверный пароль"})
    return templates.TemplateResponse("login.html",
                                       {"request": request, 
                                        "error": "Неверный логин"})

@app.get("/logout", response_class=HTMLResponse)
def logout(request: Request):
    try:
        session_id = request.cookies.get("session_id")
        print(session_id)
        del sessions[session_id]
        # return RedirectResponse(url="/")
        return templates.TemplateResponse("login.html", {"request": request, 
                                        "message": "Сессия завершена из-за действия пользователя",
                                        "url": "/login"})
    except:
        return RedirectResponse(url="/")
    

@app.get("/home/{username}", response_class=HTMLResponse)
def get_start_page(request: Request, username: str):
    refresh_session(request)
    users = load_users()
    user = users.get(username)
    if not user:
        return RedirectResponse("/")
    return templates.TemplateResponse("main.html", {"request": request, "user": user})

@app.get("/404", response_class=HTMLResponse)
def get_start_page(request: Request):
    return templates.TemplateResponse("404.html", {"request": request})

@app.exception_handler(404)
def not_found_page(request: Request, exc):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        return RedirectResponse(url="/404")
    else:
        return RedirectResponse(url="/")
    
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    admin_login: str = Form(...),
    admin_password: str = Form(...),
    avatar: UploadFile = File(None)
):
    # print(username)
    # Проверка на заполненность
    if not username or not password or not admin_login or not admin_password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Все поля, кроме аватара, обязательны!"}
        )

    # Проверка админа
    if admin_login != ADMIN_LOGIN or admin_password != ADMIN_PASSWORD:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Неверные данные администратора!"}
        )

    # Проверка уникальности логина
    users = load_users()
    if username in users:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пользователь с таким логином уже существует!"}
        )

    # Сохраняем аватар
    avatar_path = "sources/default.png"
    # print(avatar.filename)
    if avatar.filename:
        # print('here')
        # print(avatar.filename)
        file_location = Path("sources") / avatar.filename
        

        # Сохраняем временно
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

        # Открываем и ресайзим
        img = Image.open(file_location)
        width, height = img.size

        if height > 300:
            # вычисляем новый размер с сохранением пропорций
            new_height = 300
            new_width = int(width * (new_height / height))
            img = img.resize((new_width, new_height), Image.LANCZOS)
            img.save(file_location)

        avatar_path = str(file_location)


    # Сохраняем пользователя
    save_user(username, password, avatar_path)

    return templates.TemplateResponse(
            "register.html",
            {"request": request, "message": "Пользователь успешно создан!"}
        )