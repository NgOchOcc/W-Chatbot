from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.collection import ChatbotConfiguration
from weschatbot.utils.db import provide_session


class ChatbotConfigurationService(LoggingMixin):
    @provide_session
    def get_configuration(self, session=None):
        res = session.query(ChatbotConfiguration).first()
        return res

    @provide_session
    def get_collection_name(self, session=None):
        configuration = self.get_configuration(session)
        return configuration.collection.name

    @provide_session
    def get_prompt(self, session=None):
        configuration = self.get_configuration(session)
        return configuration.prompt
