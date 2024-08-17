import datetime
import json

import numpy as np
import torch
from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol

from data_source import AudioDataSource, DescriptiveError
from med.handler import MedHandler
from msc.handler import MscHandler


def error_message(error: DescriptiveError):
    return json.dumps({
        "type": "error",
        "data": {
            "error": error.error,
            "message": error.description,
        }
    })

def progress_update(progress_percentage: float, message: str):
    return json.dumps({
        "type": "progress",
        "data": {
            "progress": f"{progress_percentage}%",
            "message": message
        }
    })

connected_clients = set()

async def handler(ws,med_handler: MedHandler, msc_handler: MscHandler, audio_data_source: AudioDataSource) -> None:

    connected_clients.add(ws)

    print("Client connected")
    print("Number of connected clients: ", len(connected_clients))

    try:
        async for message in ws:

        # Decode the message and check if it is an expected message type
            try:
                json_message = json.loads(message) if (isinstance(message, str)) else message
            except Exception as e:
                error = DescriptiveError('format_error', "Invalid JSON", f"Error thrown when decoding message from client. {str(e)}", 400)  
                await ws.send(error_message(error))
                await ws.close()
                return
            
            if "type" not in json_message:
                error = DescriptiveError('format_error', "Invalid request", "Message does not contain a 'type' field", 400)
                await ws.send(error_message(error))
                await ws.close()
                return
        
            recording_id = json_message["recording_id"] if "recording_id" in json_message else None
            recording_bytes = np.array(json_message['bytes'] ) if 'bytes' in json_message else None

            if recording_id is None and recording_bytes is None:
                error = DescriptiveError('format_error', "Invalid request", "Message does not contain a 'recording_id' field", 400) 
                await ws.send(error_message(error))
                await ws.close()
                return
            
            type = json_message["type"]
            match type.lower():
                case "med":
                    try:
                        await ws.send(progress_update(0.0, "Preparing the recording for the MED model"))
                        if recording_id is not None: 
                            print("handling recording_id")
                            await handle_med_request(recording_id, med_handler,audio_data_source, ws)
                        elif recording_bytes is not None: 
                            print("handling bytes")
                            await handle_med_request_bytes(recording_bytes, med_handler, ws)

                    except DescriptiveError as e:
                        await ws.send(error_message(e))

                        return
                    except Exception as e:
                        error = DescriptiveError('internal_error', "Internal server error", f"An error occurred while processing the request. {str(e)}", 500)
                        await ws.send(error_message(error))
                        await ws.close()
                        return
                case "msc":
                    try:
                        await ws.send(progress_update(0.0, "Preparing the recording for the MSC model"))
                        await handle_msc_request(recording_id,msc_handler,audio_data_source, ws)
                        await ws.close()
                    except DescriptiveError as e:
                        await ws.send(error_message(e))
                        await ws.close()
                        return
                    except Exception as e:
                        error = DescriptiveError('internal_error', "Internal server error", f"An error occurred while processing the request. {str(e)}", 500)
                        await ws.send(error_message(error))
                        await ws.close()
                        return
                case _:
                    error = DescriptiveError('format_error', "Invalid request type", f"'type' can only be one of the following values ['msc','med'] but was {type}", 400)
                    await ws.send(error_message(error))
                    await ws.close()
                    return
    except ConnectionClosed:
        print("Client disconnected")
    finally:
        print("Removing client from connected clients")
        connected_clients.remove(ws)


async def handle_med_request(recording_id, med_handler: MedHandler, data_source: AudioDataSource, ws):
    async def on_progress_update(progress_percentage: float, message: str):
        await ws.send(progress_update(progress_percentage,message))
    await on_progress_update(0.0, "Fetching recording from database.")
    # Load recording from the database
    try:
        recording = data_source.fetch(recording_id)
    except DescriptiveError as e:
        await ws.send(error_message(e))
        await ws.close()
        return
    
    await on_progress_update(0.0, "Pre-processing the audio recording.")
    # Prepare the recording for the MED model
    input = med_handler.prepare(recording.bytes)
    result = await med_handler.run(recording=recording, signal=input.numpy(), send_update_to_client=on_progress_update)
    _, path = med_handler.generate_outputs(result)

    await ws.send(json.dumps({"type": "complete", "data": {
        "recording_id": recording_id,
        "path": path.as_uri()
    }}))

# This here is the signal of the wav - this is the PCM data without the header.
# When the caller sends audio bytes, they will need to remember this.
async def handle_med_request_bytes(recording_bytes: np.ndarray, med_handler:MedHandler, ws: WebSocketServerProtocol):
    async def on_progress_update(progress_percentage: float, message: str):
        await ws.send(progress_update(progress_percentage,message))

    results = await med_handler.run_bytes(torch.FloatTensor(recording_bytes), on_progress_update)

    await ws.send(json.dumps({"type": "complete", "data": {
        "predictions": results.tolist(),
    }}))


async def handle_msc_request(recording_id, msc_handler: MscHandler, data_source: AudioDataSource,ws):    

    async def on_progress_update(progress_percentage: float, message: str):
        await ws.send(progress_update(progress_percentage,message))
    
    # Load recording from the database
    try:
        recording = data_source.fetch(recording_id)
    except DescriptiveError as e:
        await ws.send(error_message(e))
        await ws.close()
        return
    try:
        msc_input = data_source.load_med_output_for_recording(recording)
    except DescriptiveError as e:
        await ws.send(error_message(e))
        await ws.close()
        return
    except Exception as e:
        error = DescriptiveError('internal_error', "Internal server error", f"An error occurred while processing the request. {str(e)}", 500)
        await ws.send(error_message(error))
        await ws.close()
        return
        
    await on_progress_update(0.0, "Loaded MED recording, beginning MSC.")
    msc_result = await msc_handler.run(recording=recording, signal=msc_input,send_update_to_client=on_progress_update)
    await on_progress_update(100, "MSC finished, generating outputs.")
    path = msc_handler.generate_outputs(recording=recording, result=msc_result)

    await ws.send(json.dumps({"type": "complete", "data": {
        "recording_id": recording_id,
        "path": path,
    }}))
