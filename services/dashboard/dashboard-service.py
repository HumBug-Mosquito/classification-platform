import os

import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketState

from lib.classifier import Classifier
from lib.exceptions import DescriptiveError
from lib.types import Environment
from services.dashboard.processing_queue import ProcessingQueue
from services.dashboard.processing_recordings import PendingRecording

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

processing_queue = ProcessingQueue(classifier)

@app.websocket("/updates")
async def handle_new_client(websocket: WebSocket):
    await websocket.accept()

    processing_queue.watch(websocket)
    try:
        while not websocket.client_state== WebSocketState.DISCONNECTED:
            message = await websocket.receive()  # This will block until a message is received
            if message is None:
                break
    except DescriptiveError as e:
        print(f"Descriptive error: {e.description}")
        
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        print("Removing client")
        processing_queue.remove_general_observer(websocket)
        
@app.websocket("/med/{recording_id}")
async def handle_recording_client(websocket: WebSocket, recording_id: str):
    await websocket.accept()

    processing_queue.watch_recording(recording_id, websocket)
    processing_queue.add(PendingRecording.med(recording_id))
    
    try:
        while not websocket.client_state== WebSocketState.DISCONNECTED:
            message = await websocket.receive()  # This will block until a message is received
            if message is None:
                break
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        print("Removing client")
        processing_queue.remove_recording_observer(recording_id)