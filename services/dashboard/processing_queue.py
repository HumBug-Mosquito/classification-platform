import asyncio
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from logging import Logger, getLogger

from fastapi import WebSocket

from lib.classifier import Classifier
from lib.exceptions import UserCancelledError
from services.dashboard.processing_recordings import (PendingRecording,
                                                      ProcessingRecording)

queue_thread = ThreadPoolExecutor()

class ProcessingQueue:
    logger: Logger
    general_observers: list[WebSocket] = []
    recording_observers: dict[str, WebSocket] = {}
    classifier: Classifier

    current_processing: ProcessingRecording | None = None
    queue = deque[PendingRecording]()

    def __init__(self, classifier: Classifier):
        self.classifier = classifier
        self.general_observers = []
        self.recording_observers = {}
        self.logger = getLogger(__name__)   
        self.loop = asyncio.get_event_loop()
        
    def add(self, pending_recording: PendingRecording):
        self.queue.append(pending_recording)
        self.logger.info(f"Added recording {pending_recording.recording_id}. Queue size: {len(self.queue)}")
        self.update_general_observers() 
        self.process()
        
    def process(self):
        if self.current_processing is not None or len(self.queue) == 0:
            self.logger.info(f"No recordings to process. Current processing: {self.current_processing}, queue size: {len(self.queue)}")
            return
        
        recording = self.queue.popleft()
        abort_signal = threading.Event()
        
        task = asyncio.get_event_loop().run_in_executor(
            queue_thread, self.perform_task, recording, abort_signal 
        )
        
        self.current_processing = ProcessingRecording(recording_id=recording.recording_id, type=recording.type, task=task, abort_signal=abort_signal)
        self.update_general_observers()
        
    def perform_task(self, recording: PendingRecording, abort_signal: threading.Event):
        def update_recording_observers(progress: float, status: str):
            self.current_processing.progress = progress
            self.current_processing.status = status
            self.update_general_observers()
        
            if recording.recording_id in self.recording_observers:
                recording_observer = self.recording_observers[recording.recording_id]
                self.send_message_to_client(recording_observer, {"type": "progress", "data": self.current_processing.dict()})

        try:
            print(f"Processing recording {recording.recording_id}")
            match recording.type:
                case "med":
                    path = self.classifier.med_recording(recording.recording_id, abort_signal=abort_signal, send_update_to_client=update_recording_observers)
                    update_recording_observers(100, "completed, path: " + path)
                case "msc":
                    print("Not implemented yet")
            
            print("task completed")
            self.current_processing = None
            self.update_general_observers()
            self.process()
            
        except UserCancelledError:
            print("cancelled")
            update_recording_observers(100, "cancelled")
        except Exception as e:
            print(f"Error processing recording: {str(e)}")
            update_recording_observers(100, f"error: {str(e)}")
        finally:
            self.current_processing = None
            self.update_general_observers()
            self.process()

    def watch(self, client: WebSocket):
        self.general_observers.append(client)
        self.update_general_observers()
        print(f"Added general observer. Total observers: {len(self.general_observers)}")
        

    def watch_recording(self, recording_id: str, client: WebSocket):
        self.recording_observers[recording_id] = client
        
        if self.current_processing is not None and self.current_processing.recording_id == recording_id:
            self.send_message_to_client(client, {"type": "progress", "data": self.current_processing.dict()})
           
    def cancel(self, recording_id: str):
        if self.current_processing.recording_id == recording_id: 
            self.current_processing.cancel()
            self.current_processing = None
            
        for b in self.queue:
            if b.recording_id == recording_id:
                self.queue.remove(b)
                break
            
    def remove_general_observer(self, client: WebSocket):
        self.general_observers.remove(client)
        
    def remove_recording_observer(self, recording_id: str):
        if recording_id in self.recording_observers:
            del self.recording_observers[recording_id]

    def update_general_observers(self):
        # print(f"Updating general observers. Current processing: {self.current_processing.recording_id if self.current_processing is not None else None}, queue size: {len(self.queue)}")
        for client in self.general_observers:
            message = {
                "processing": self.current_processing.dict() if self.current_processing is not None else None,
                "queue": [recording.dict() for recording in self.queue],
            }
            print(f"Sending: {message}")
            self.send_message_to_client(client, message)
            
    def send_message_to_client(self, client: WebSocket, message: dict):
        try:
            asyncio.run_coroutine_threadsafe(client.send_json(message), self.loop)
        except RuntimeError:
            # Handle the case where the WebSocket is closed
            print(f"Failed to send message to client. WebSocket might be closed.")