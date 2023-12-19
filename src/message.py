class MessageType(type):
    ERROR = 'ERROR'
    DATA = 'DATA',
    LOADING = 'LOADING'
    CLASSIFICATION = 'CLASSIFICATION'

class Message(object):

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        return

    def __str__(self) -> str:
        return "Message: " + str(self.payload)
    

class OutgoingMessage(Message):
    def __init__(self, type: MessageType, text_override=None) -> None:
        self.type = type

        text = text_override

        if (text_override == None):
            match(self.type):
                case Message.ERROR:
                    text = 'There was an error during the processing of your request.'

        payload = dict({
            'type': type, 
            'data': {
                "text": text
            }
        })

        Message.__init__(self,payload)
        return

class ErrorMessage(OutgoingMessage):
    def __init__(self, text='There was an error during the processing of your request.'):

        OutgoingMessage.__init__(self, MessageType.ERROR, text)
        return


class ClassificationResponseMessage(OutgoingMessage):

    def __init__(self, text_override=None, predictions=[]):
        self.predictions = predictions
        OutgoingMessage.__init__(self, type=MessageType.CLASSIFICATION, text_override=text_override)
        self.payload.get('data').update({"predictions": predictions})








# Incoming messages

class IncomingMessage(Message): 
    
    def __init__(self, payload: dict):
        Message.__init__(self, payload=payload)
        return


# Allowed types: ['audio']
def get_incoming_message_from_json(json: dict) -> tuple | IncomingMessage:
        if ('type' not in json):
            return 400, 'No "type" property was provided.'


        match(json.get('type')):
            case 'audio':
                if ('bytes' not in json):
                    return 400,'No "bytes" property was provided as expected in all audio messages'
                elif ('name' not in json):
                    return  400, 'No "name" property provided as expected in all audio messages'
                
                try:
                    return AudioMessage.fromJson(json)
                except Exception as e:
                    return 500, 'Unable to cast message to AudioMessage: JSON deserialization failed. ' + str(e)
            
            case _:
                return 400, 'Unknown type provided ' + json.get('type')


class AudioMessage(IncomingMessage):
    def __init__(self, name, bytes, json):
        self.name = name
        self.bytes = bytes
        IncomingMessage.__init__(self, json)

    def fromJson(json: dict):
        return AudioMessage(bytes=json.get('bytes'), name=json.get('name'), json=json)
        