FROM node:slim AS node_builder

WORKDIR /opt/app

COPY . ./

RUN cd weschatbot/www \
    && npm i \
    && npm run build

CMD []


FROM chatbot-base:0.0.1 AS weschatbot_app

EXPOSE 8000

WORKDIR /opt/app

RUN pip install build

COPY . ./

COPY --from=node_builder /opt/app/weschatbot/www/static/chatbot_ui/dist /opt/app/weschatbot/www/static/chatbot_ui/dist
COPY --from=node_builder /opt/app/weschatbot/www/static/management/dist /opt/app/weschatbot/www/static/management/dist


RUN python -m build \
    && pip install dist/weschatbot-0.0.1-py3-none-any.whl

CMD []