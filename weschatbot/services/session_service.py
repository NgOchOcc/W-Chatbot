import pickle

from weschatbot.exceptions.user_exceptions import UserNotFoundError
from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.user import ChatSession, ChatMessage, User
from weschatbot.schemas.chat import Chat
from weschatbot.utils.db import provide_session
from weschatbot.utils.redis_config import provide_redis, DB_CHAT


class NotPermissionError(Exception):
    pass


class SessionService(LoggingMixin):
    KEY_FMT = 'ss_{chat_id}'
    REDIS_DB = DB_CHAT

    @provide_redis(REDIS_DB)
    def store_chat(self, chat, redis_client):
        redis_client.set(self.KEY_FMT.format(chat_id=chat.chat_id), pickle.dumps(chat.messages))

    @provide_redis(REDIS_DB)
    def get_chat(self, chat_id, redis_client):
        messages = pickle.loads(redis_client.get(self.KEY_FMT.format(chat_id=chat_id)))
        return Chat(messages=messages, chat_id=chat_id)

    def create_session(self):
        import uuid
        chat_id = str(uuid.uuid4())
        chat = Chat([], chat_id)
        self.store_chat(chat)
        return chat_id, chat

    def get_session(self, chat_id):
        chat = self.get_chat(chat_id)
        return chat

    @provide_session
    def add_session_in_db(self, user_id, chat_id, messages, session=None):

        inserted_message_ids = []

        def add_messages(db_chat_id):
            for message in messages:
                new_message = ChatMessage(
                    name=message.message[0:31],
                    content=message.message,
                    sender=message.sender,
                    chat_id=db_chat_id
                )
                session.add(new_message)
                session.flush()
                inserted_message_ids.append((new_message.id, message.sender))

        chat = session.query(ChatSession).filter(ChatSession.uuid == chat_id).first()
        if chat:
            add_messages(chat.id)
        else:
            new_chat = ChatSession(
                name=messages[0].message[0:31],
                uuid=chat_id,
                user_id=user_id,
                status_id=1
            )
            session.add(new_chat)
            session.commit()
            session.refresh(new_chat)

            add_messages(new_chat.id)

        return inserted_message_ids

    def update_session(self, user_id, chat_id, messages):
        chat = self.get_chat(chat_id)
        chat.messages = chat.messages + messages
        inserted_message_ids = self.add_session_in_db(user_id, chat_id, messages)
        self.store_chat(chat)
        return inserted_message_ids

    @provide_session
    def delete_session(self, user_id, chat_id, session=None):
        chat_session = session.query(ChatSession).filter(ChatSession.uuid == chat_id).first()

        if chat_session and chat_session.user_id == user_id:
            chat_session.status_id = 2
            deleted_user = session.query(User).filter(User.name == "anonymous").one_or_none()
            if deleted_user:
                chat_session.user_id = deleted_user.id
            else:
                raise UserNotFoundError("User: anonymous not found")
        else:
            raise NotPermissionError("This session doesn't belong to you")

    @provide_session
    def get_sessions(self, user_id, session=None):
        def query_sessions(ss=None):
            return ss.query(ChatSession).filter(ChatSession.user_id == user_id).filter(ChatSession.status_id == 1).all()

        res = query_sessions(session)
        return [x.to_dict(session=session) for x in res]

    @provide_session
    def delete_chat_session_by_id(self, chat_id, session=None):
        chat = session.query(ChatSession).get(chat_id)
        if not chat:
            return False

        session.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).delete()
        session.delete(chat)
        return True
