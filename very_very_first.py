#  python -m uvicorn very_very_first:app --reload --ssl-keyfile=key.pem --ssl-certfile=cert.pem


from datetime import datetime

from fastapi import FastAPI, Form, Request, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match
import pandas as pd
import hashlib
import shutil
import uuid
import os

AVATAR_DIR = "images"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="new_templates")


@app.get('/', response_class=HTMLResponse)
@app.get('/home', response_class=HTMLResponse)
def getMain(request:Request):
    return templates.TemplateResponse(request=request, name='home.html')


@app.get('/403', response_class=HTMLResponse)
def get403(request:Request):
    return templates.TemplateResponse(request=request, name='403.html')


@app.get('/404', response_class=HTMLResponse)
def get404(request:Request):
    return templates.TemplateResponse(request=request, name='404.html')

@app.post('/register')
def postRegister(request:Request, name: str = Form(...), surname: str = Form(...), email: str = Form(...), password: str = Form(...), img: UploadFile = File(...)):
    newPassword = hash_password(password)
    ext = os.path.splitext(img.filename)[1]
    new_filename = f'{uuid.uuid4()}{ext}'
    file_path = os.path.join(AVATAR_DIR, new_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(img.file, buffer)
    avatar_url = f"/images/{new_filename}"
    df = pd.DataFrame({'name' : name, 
                       'surname' : name, 
                       'email' : email, 
                       'password' : newPassword,
                       'imgPath' : avatar_url})
    df.to_csv('UserList.csv', index=False, encoding="utf-8")
    response = RedirectResponse(url='/main', status_code=303)
    response.set_cookie(key='name', value=name, https_only=True, secure=True, samesite='lax')
    response.set_cookie(key='avatar', value=avatar_url, https_only=True, secure=True, samesite='lax')
    return response
    

@app.get('/register', response_class=HTMLResponse)
def getRegister(request:Request):
    return templates.TemplateResponse(request=request, name='register.html')


@app.get('/login', response_class=HTMLResponse)
def getLogin(request:Request):
    return templates.TemplateResponse(request=request, name='login.html')


@app.get('/main', response_class=HTMLResponse)
def getMain(request:Request):
    name = request.cookies.get('name')
    print(name)
    avatar = request.cookies.get('avatar')
    return templates.TemplateResponse(request=request, name='main.html', context={'name' : name, 'avatar' : avatar})