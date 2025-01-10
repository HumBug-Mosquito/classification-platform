import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import librosa
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
WEBSOCKET_URL = "ws://localhost:8002/msc"

RECORDING_PRESENCE = "lib/storage/test_audio_on_off.wav"
ANOPH_ARABIEN = "lib/storage/anoph_arabien.wav"
RECORD= "lib/storage/record.wav"
RECORDING_NO_PRESENCE = "lib/storage/test_no_presence.wav"  # Update this with your test file path

async def connect_and_test():
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            logger.info("Connected to WebSocket server")
            
            # Read and send the audio file
            file_path = Path(ANOPH_ARABIEN)
            if not file_path.exists():
                raise FileNotFoundError(f"Test file not found: {file_path}")
            
            signal, _ = librosa.load(file_path,sr= 8000)
                
            logger.info(f"Sending file: {file_path.name}")
            await websocket.send(json.dumps(signal.tolist()))
            
            # Listen for responses until the connection is closed
            while True:
                try:
                    response = await websocket.recv()
                    try:
                        # Try to parse as JSON
                        parsed_response = json.loads(response)
                        print(parsed_response)
                        logger.info(f"Received JSON: {json.dumps(parsed_response, indent=2)}")
                    except json.JSONDecodeError:
                        # If not JSON, log as raw message
                        logger.info(f"Received raw message: {response}")
                        
                except :
                    logger.info("WebSocket connection closed")
                    break
                
    except Exception as e:
        logger.error(f"An error occurred: {e}")

def main():
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Add file handler for logging to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(f"logs/websocket_test_{timestamp}.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Run the async test
    asyncio.run(connect_and_test())

if __name__ == "__main__":
    main()
