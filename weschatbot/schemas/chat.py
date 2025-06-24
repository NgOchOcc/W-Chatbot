class Message:
    def __init__(self, sender, receiver, message):
        self.sender = sender
        self.receiver = receiver
        self.message = message

    def to_dict(self):
        return {
            'sender': self.sender,
            'receiver': self.receiver,
            'message': self.message
        }


class Chat:
    def __init__(self, messages, chat_id, in_db=False):
        self.messages = messages
        self.chat_id = chat_id
        self.in_db = in_db

    def to_dict(self):
        return {
            'messages': [x.to_dict() for x in self.messages],
            'chat_id': self.chat_id,
            'in_db': self.in_db
        }
