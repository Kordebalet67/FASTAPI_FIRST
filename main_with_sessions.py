from fastapi import FastAPI, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from datetime import datetime, timedelta
import uuid
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import csv


app = FastAPI()
# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/images", StaticFiles(directory="images"), name="images")
templates = Jinja2Templates(directory="templates")
USERS_FILE = "user.csv"

sessions = {}
SESSION_TTL = timedelta(minutes=10)

@app.middleware("http")
async def check_session(request: Request, call_next):
    # Разрешаем доступ к главной, login/logout и ко всей статике
    if request.url.path.startswith("/static") or request.url.path in ["/", "/login", "/logout"]:
        return await call_next(request)

    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return RedirectResponse(url="/login")

    created_at = sessions[session_id]
    if datetime.now() - created_at > SESSION_TTL:
        del sessions[session_id]
        return RedirectResponse(url="/login")

    return await call_next(request)

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
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    users = load_users()
    user = users.get(username)
    if user and password == user["password_hash"]:
        session_id = str(uuid.uuid4())
        sessions[session_id] = datetime.now()
        response = RedirectResponse(url=f"/home/{username}", status_code=302)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Неверный логин или пароль"}
    )
"""    
    response = RedirectResponse(url="/home/{username}", status_code=302)
    return response
    users = load_users()
    user = users.get(username)
    if user and verify_password(password, user["password_hash"]):
        return RedirectResponse(url=f"/home/{username}", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Неверный логин или пароль"}
    )
"""

@app.get("/home/{username}", response_class=HTMLResponse)
def home(request: Request, username: str):
    users = load_users()
    user = users.get(username)
    if not user:
        return RedirectResponse("/")
    return templates.TemplateResponse("home.html", {"request": request, "user": user})

@app.get("/protected")
async def protected():
    return {"message": "Это защищённая страница!"}

@app.get("/profile")
async def profile():
    return {"user": "demo_user", "info": "Ваш профиль"}

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    response = RedirectResponse(url="/")
    response.delete_cookie("session_id")
    return response