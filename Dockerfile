FROM node:slim AS node_builder

WORKDIR /opt/app

COPY . ./

RUN cd weschatbot/www \
    && npm i \
    && npm run build

CMD []


FROM python:3.12.4 AS weschatbot_app

WORKDIR /opt/app

RUN pip install build

COPY . ./

COPY --from=node_builder /opt/app/weschatbot/www/static/weschatbot/dist /opt/app/weschatbot/www/static/weschatbot/dist


RUN python -m build \
    && pip install dist/weschatbot-0.0.1-py3-none-any.whl

CMD []