import os

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketState
from fastapi.middleware.cors import CORSMiddleware

from lib.classifier import Classifier
from lib.types import Environment

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

classifier = Classifier(Environment(os.environ))

@app.websocket("/med")
async def event_detection(websocket: WebSocket):
    await websocket.accept()
    
    while websocket.client_state == WebSocketState.CONNECTED:
        bytes = await websocket.receive_bytes()
        if (bytes is None): break
        
        # np_bytes = np.frombuffer(bytes, dtype=np.int16)
        # classifier.predict(np_bytes)