# python -m uvicorn very_first:app --reload

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import pandas as pd
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.add_middleware(SessionMiddleware, secret_key="krivobotkrivobotkrivobot")

white_urls = ["/", "/login", "/logout", "/register"]

# Маршрутизация приложения
@app.get("/", response_class=HTMLResponse) # перехват адреса http://localhost:8000/
def main_page(request: Request):
    return templates.TemplateResponse(request=request, name ="based_main.html")

@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    username = request.session.get('username')
    password_hash = request.session.get('password_hash')
    if not username:
        return RedirectResponse(url="/login", status_code=302)
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
        response = RedirectResponse(url=f"/home", status_code=302)
        return response
    else:
        return templates.TemplateResponse({"request": request, 
                                        "error": "Неверный пароль или логин"},
                                        name="login.html")



@app.get("/404", response_class=HTMLResponse)
def _404_page(request: Request):
    return templates.TemplateResponse(request=request, name="404.html")