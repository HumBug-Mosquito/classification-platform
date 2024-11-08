import asyncio
import threading
from asyncio import Future
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from lib.exceptions import UserCancelledError


class PendingRecording:
    def __init__(self, recording_id: str, type: str):
        self.recording_id = recording_id
        self.type = type
    
    @staticmethod
    def med(recording_id: str):
        return PendingRecording(recording_id, "med")  
    
    @staticmethod
    def msc(recording_id: str): 
        return PendingRecording(recording_id, "msc")

    def __str__(self):
        return f"RecordingToBeProcessed(recording_id={self.recording_id}, type={self.type})"
    
    def dict(self):
        return {
            "recording_id": self.recording_id,
            "type": self.type
        }
    
class ProcessingRecording:
    def __init__(self, recording_id: str, type: str,task: Future,abort_signal: threading.Event) -> None:
        self.recording_id = recording_id
        self.progress = 0
        self.status = "Not started"
        self.type = type
        self.task = task
        self.abort_signal = abort_signal    
        pass

    def cancel(self):
        print("Cancelling task")    
        self.abort_signal.set()
        if not self.task.done():
            self.task.cancel()

    def update(self, progress: int, status: str):
        self.progress = progress
        self.status = status
    
    def dict(self):
        return {
            "recording_id": self.recording_id,
            "progress": self.progress,
            "status": self.status,
            "type": self.type
        }
