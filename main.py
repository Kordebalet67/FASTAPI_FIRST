import csv
import os
import shutil
from pathlib import Path
import hashlib
from PIL import Image
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="images"), name="images")
templates = Jinja2Templates(directory="templates")

# Файл для хранения пользователей
USERS_FILE = "users.csv"

# Фейковый админ
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "1234"

# Проверяем, есть ли CSV, если нет — создаём
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "password_hash", "avatar_path"])


# --- Хэширование через SHA-256 ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def save_user(username: str, password: str, avatar_path: str):
    """Сохраняем пользователя в CSV"""
    password_hash = hash_password(password)
    with open(USERS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([username, password_hash, avatar_path])


def load_users():
    """Загружаем всех пользователей из CSV"""
    users = {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users[row["username"]] = {
                "username": row["username"],
                "password_hash": row["password_hash"],
                "avatar": row["avatar_path"]
            }
    return users


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    users = load_users()
    user = users.get(username)
    if user and verify_password(password, user["password_hash"]):
        return RedirectResponse(url=f"/home/{username}", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Неверный логин или пароль"}
    )


@app.get("/home/{username}", response_class=HTMLResponse)
def home(request: Request, username: str):
    users = load_users()
    user = users.get(username)
    if not user:
        return RedirectResponse("/")
    return templates.TemplateResponse("home.html", {"request": request, "user": user})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    admin_login: str = Form(...),
    admin_password: str = Form(...),
    avatar: UploadFile = File(None)
):
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
    # Сохраняем аватар
    avatar_path = "images/default.png"
    if avatar:
        file_location = Path("images") / avatar.filename

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

    return RedirectResponse("/", status_code=302)
