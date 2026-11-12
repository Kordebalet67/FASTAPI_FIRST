# python -m uvicorn very_first:app --reload ПОКА НЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕЕ
# & "C:\Program Files\Git\usr\bin\openssl.exe" req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365
# ВЕРХНЮЮ СТРОЧКУ В БАШ
# uvicorn main:app --reload --ssl-keyfile=key.pem --ssl-certfile=cert.pem
# python -m uvicorn very_first:app --reload --ssl-keyfile=key.pem --ssl-certfile=cert.pem
from datetime import datetime

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match
import pandas as pd
import hashlib

SESSION_LIFETIME = 60
white_urls = ["/", "/login", "/logout", "/register"]

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.middleware("http")
async def session_activity_middleware(request: Request, call_next):
    path = request.url.path

    if path.startswith("/static") or path in white_urls or request.url.path.startswith("/sources"):
        return await call_next(request)

    route_exists = False
    for route in app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            route_exists = True
            break
    if not route_exists:
        return await call_next(request)

    if not request.session.get("username"):
        return templates.TemplateResponse(
            request=request,
            name="403.html",
            context={"detail": "Доступ запрещен или время сессии истекло."},
            status_code=403,
        )


    
    request.session["last_activity"] = str(datetime.now())
    print(datetime.now())

    return await call_next(request)

app.add_middleware(SessionMiddleware,
                    secret_key="krivobotkrivobotkrivobot",
                    max_age=SESSION_LIFETIME, 
                    https_only=True)


# Маршрутизация приложения
@app.get("/", response_class=HTMLResponse) # перехват адреса http://localhost:8000/
def main_page(request: Request):
    return templates.TemplateResponse(request=request, name ="based_main.html")

@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    # print(datetime.now(), request.session.get('session_starttime'))
    username = request.session.get('username')
    password_hash = request.session.get('password_hash')
    if not username:
        return RedirectResponse(url="/403", status_code=302)

    return templates.TemplateResponse(request=request, 
                                      name="home.html", 
                                      context={'username': username, 
                                               'password_hash': password_hash})


users = [{'username' : 'admin', 'password' : hash_password('1111' + 'admin')}]
df = pd.DataFrame(users)
df.to_csv("krivousers.csv", index=False, encoding="utf-8")

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")


@app.post("/register")
def register(request: Request,
            password: str = Form(...), 
            username: str = Form(...)):
    res = ''
    df = pd.read_csv('krivousers.csv')
    users_new = df.to_dict(orient="records")
    print(users_new)
    for i in users_new:
        if username == i['username']:
            res = 'ужес exist'
            break
    if res == 'ужес exist':
        return templates.TemplateResponse(name="register.html",
                                        request=request, 
                                        context={"error": res})
    else:
        new_user = pd.DataFrame([{'username' : username, 'password' : hash_password(password + username)}])
        new_user.to_csv('krivousers.csv', mode="a", index=False, header=False, encoding="utf-8")
        request.session['username'] = username
        request.session['password_hash'] = hash_password(password + username)
        request.session['session_starttime'] = str(datetime.now())
        response = RedirectResponse(url=f"/home", status_code=302)
        return response
    
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
def login(request: Request,
          password: str = Form(...), 
          username: str = Form(...) 
          ):
    df = pd.read_csv('krivousers.csv')
    users_new = df.to_dict(orient="records")
    print(users_new)
    res = 'neverno'
    for i in users_new:
        if username == i['username'] and hash_password(password + username) == i['password'] :
            res = 'успешно'
            break

    if res == 'успешно':
        request.session["username"] = username
        request.session['password_hash'] = hash_password(password + username)
        request.session['session_starttime'] = str(datetime.now())
        response = RedirectResponse(url=f"/home", status_code=302)
        return response
    else:
        return templates.TemplateResponse(request=request,
                                          name="login.html",
                                        context={"error": "Неверный пароль или логин"},
                                        )



@app.exception_handler(404)
def not_found_exception_handler(request: Request, exc: StarletteHTTPException):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        status_code=404,
    )

@app.get("/403", response_class=HTMLResponse)
def forbidden_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="403.html",
        status_code=403,
    )