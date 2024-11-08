import asyncio
import json
import os
import threading

import numpy as np
import pandas as pd
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketDisconnect, WebSocketState

from lib.classifier import Classifier
from lib.custom_types import Environment
from lib.exceptions import DescriptiveError

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

classifier = Classifier(Environment(dict(os.environ)))
# Set Pandas options to display full DataFrame in logs
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/med")
async def event_detection(websocket: WebSocket):
    await websocket.accept()

    abort_signal = threading.Event()
    def on_progress(progress: float, status: str):
        if (websocket.client_state == WebSocketState.CONNECTED):
            asyncio.run_coroutine_threadsafe(websocket.send_text(json.dumps({"type": "progress", "data": {"progress": progress, "message": status}})), asyncio.get_event_loop() )

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            message = await websocket.receive_text()
            if (message is None): break

            bytes = json.loads(message)
            np_bytes = np.array(bytes, dtype=np.float32)

            events = classifier.med(np_bytes, send_update_to_client=on_progress, abort_signal=abort_signal)
            completed_message ={"type": "complete", "data": events.__dict__()}
            await websocket.send_json(completed_message)

    except DescriptiveError as e:
        print(f"Descriptive error: {e.description}")
        await websocket.send_text(json.dumps({"type": "error", "data":e.__dict__()  }))

    except WebSocketDisconnect as e:
        print("Client disconnected")
    finally:
        if not abort_signal.is_set():
            abort_signal.set()
        print("Connection closed")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()


@app.websocket("/msc")
async def species_classification(websocket: WebSocket):
    await websocket.accept()
    
    abort_signal = threading.Event()
    def on_progress(progress: float, status: str):
        if (websocket.client_state == WebSocketState.CONNECTED):
            asyncio.run_coroutine_threadsafe(websocket.send_text(json.dumps({"type": "progress", "data": {"progress": progress, "message": status}})), asyncio.get_event_loop() )

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            message = await websocket.receive_text()
            if (message is None): break

            bytes = json.loads(message)
            np_bytes = np.array(bytes, dtype=np.float32)

            events = classifier.msc(np_bytes, send_update_to_client=on_progress, abort_signal=abort_signal)
            completed_message ={"type": "complete", "data": events.__dict__()}
            await websocket.send_json(completed_message)

    except DescriptiveError as e:
        print(f"Descriptive error: {e.description}")
        await websocket.send_text(json.dumps({"type": "error", "data":e.__dict__()  }))

    except WebSocketDisconnect as e:
        print("Client disconnected")
    finally:
        if not abort_signal.is_set():
            abort_signal.set()
        print("Connection closed")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()