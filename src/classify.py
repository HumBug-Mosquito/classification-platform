#!/usr/bin/env python


from json import dumps

from websockets import WebSocketServerProtocol

from message import AudioMessage, ClassificationResponseMessage


class Classifier:
    def __init__(self, model) -> None:
        pass

    """
    Performs an audio classification using the loaded model and responds to the client when ready.
    """
    async def classify_and_respond(self, websocket: WebSocketServerProtocol, audio_message: AudioMessage) -> None:

        print("Classifying the following audio:", audio_message.name)

        message = ClassificationResponseMessage(text_override='Classification complete.', predictions=[])
        await websocket.send(dumps(message.payload))

    """
    Classifies the received list of audio bytes and returns a list of predictions.
    """
    def classify_audio(bytes: list):
        return []

