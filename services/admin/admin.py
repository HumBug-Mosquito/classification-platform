import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

with open(os.path.join(os.path.dirname(__file__), "static/index.html"), 'r') as file:  # r to open file in READ mode
    html_as_string = file.read()
    
@app.get("/")
async def root():
    return HTMLResponse(content=html_as_string, status_code=200)
    