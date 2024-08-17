import asyncio
import datetime
import logging
import os
import stat
import sys

from pymongo import MongoClient
from websockets.server import serve

from data_source import AudioDataSource, DescriptiveError
from med.handler import MedHandler
from msc.handler import MscHandler
from request_handler import handler


def connect_to_database() -> MongoClient:
    database_client =  MongoClient(os.environ['DATABASE_URL'], 27017)
    return database_client

def setup_logger():
    now = datetime.datetime.now()
    today = datetime.datetime(now.year, now.month, now.day)

    simple_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    log_filename = os.environ.get('LOGS_DIR') + today.__str__() + '.log'
    
    handler = logging.FileHandler(log_filename)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    logging.basicConfig(format=simple_format, handlers=[handler])
    logger = logging.getLogger('main')
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.info("---------------------------------------------------------------------")
    return logger

def check_env(expected_env) -> None:
    for env_var in expected_env:
        if env_var not in os.environ:
            raise Exception(f"Missing environment variable: {env_var}")

    # Get environment variables
    classification_output_dir = os.environ.get('CLASSIFICATION_OUTPUT_DIR')
    logs_dir = os.environ.get('LOGS_DIR')

    # Create directories if they don't exist
    os.makedirs(classification_output_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
        

async def main() -> None:
    expected_env = ["PORT", "DATABASE_URL", "LOGS_DIR", "CLASSIFICATION_OUTPUT_DIR"]

    check_env(expected_env)

    database = connect_to_database()

    logger = setup_logger()
    logger.info("Service starting...")

    # create logs directory if it does not exist
    if not os.path.exists(os.getenv('LOGS_DIR')):
        os.makedirs(os.getenv('LOGS_DIR'))

    # create classification output directory if it does not exist
    if not os.path.exists(os.getenv('CLASSIFICATION_OUTPUT_DIR')):
        os.makedirs(os.getenv('CLASSIFICATION_OUTPUT_DIR'))

    port = os.getenv('PORT')
    logger.debug("Loading the MED model")
    med_handler: MedHandler = MedHandler()
    med_handler.load_model()
    logger.debug("Loaded the MED model")

    logger.debug("Loading the MSC model")
    msc_handler: MscHandler = MscHandler()
    msc_handler.load_model()
    logger.debug("Loaded the MSC model")

    audio_data_source = AudioDataSource(database)

    #max_size = 10MB
    async with serve(lambda ws: handler(ws, med_handler=med_handler, msc_handler=msc_handler, audio_data_source=audio_data_source), "0.0.0.0", port, max_size=10*1024*1024) : 
        logger.debug(f"Server started on port: {port}")
        print("Server started on port: ", port)
        await asyncio.Future()


asyncio.run(main())