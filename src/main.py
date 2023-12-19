import asyncio
import json
import os

from dotenv import load_dotenv
from websockets import WebSocketServerProtocol
from websockets.server import serve

from classify import Classifier
from message import (AudioMessage, ErrorMessage, IncomingMessage,
                     get_incoming_message_from_json)

load_dotenv()

def load_model(path: str):
    print("loading model at path " + path)


def check_env() -> None:
    if( not os.getenv('PORT')):
        raise Exception("PORT not defined in .env")

        
    
async def handler(websocket: WebSocketServerProtocol, classifier: Classifier) -> None:
    async for message in websocket:
        
        # Make sure the incoming message is an AudioMessage 
        # this can be extended to other IncomingMessage types
        try:
            json_message: dict = json.loads(message)
            incoming_message = get_incoming_message_from_json(json_message)
            if (not isinstance(incoming_message, AudioMessage)):
                print(incoming_message)
                print(ErrorMessage(text=incoming_message[1]).payload)
                await websocket.send(json.dumps(ErrorMessage(text=incoming_message[1]).payload))
                pass
            
        except Exception as e:
            error = ErrorMessage(text= "Error thrown when handling message from client. "+ str(e))
            await websocket.send(error.payload)
            pass

        # Given that the incoming message is an AudioMessage then we can classify it 
        try:
            await classifier.classify_and_respond(websocket, incoming_message)
        except Exception as e:
            error = ErrorMessage(text="Error thrown when classifying bytes in audio provided. " + str(e))
            print(error)
            await websocket.send(json.dumps(error.payload))
        pass
        

async def main() -> None:
    check_env()
    
    port = os.getenv('PORT')
    classifier = Classifier('')
    async with serve(lambda ws: handler(ws, classifier), "localhost", port):
        print("Server started on port: ", port)
        await asyncio.Future()


asyncio.run(main())

