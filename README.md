# Cloud Audio Processing Service

This is a python service that provides connected clients with the ability to stream audio bytes from their device to be classified and receive the results.


## Checklist

[X] - Open WebSocket server that can receive incoming messages from the client.
[] - Perform further validation on the messages such as name is in the correct format, that the audio bytes are not empty.
[] - Actually perform the classification on the audio and return a valid response.
[] - Provide a classification date to the classification results.