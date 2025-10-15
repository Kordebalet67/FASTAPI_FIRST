from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.hash import argon2

app = FastAPI()

# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Фейковая база пользователей
fake_users = {
    "admin": {
        "username": "admin",
        "password_hash": argon2.hash("1234"),
        "avatar": "https://www.vhv.rs/dpng/d/433-4337863_the-punisher-skull-symbol-icon-vector-logo-decal.png"
    }
}
print(argon2.verify(("1234"), argon2.hash("1234")))

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = fake_users.get(username)
    if user and argon2.verify(password, user["password_hash"]):
        response = RedirectResponse(url=f"/home/{username}", status_code=302)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})

@app.get("/home/{username}", response_class=HTMLResponse)
def home(request: Request, username: str):
    user = fake_users.get(username)
    if not user:
        return RedirectResponse("/")
    return templates.TemplateResponse("home.html", {"request": request, "user": user})
