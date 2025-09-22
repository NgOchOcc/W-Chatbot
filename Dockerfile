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

RUN pip install --upgrade pip setuptools wheel
RUN pip install build
RUN pip install 'uvicorn[standard]'
RUN pip install fastapi uvicorn transformers sentence-transformers pymilvus
RUN pip install vllm
RUN pip install sphinx sphinx-autobuild sphinx-rtd-theme myst_parser


COPY . ./

COPY --from=node_builder /opt/app/weschatbot/www/static/chatbot_ui/dist /opt/app/weschatbot/www/static/chatbot_ui/dist
COPY --from=node_builder /opt/app/weschatbot/www/static/management/dist /opt/app/weschatbot/www/static/management/dist

RUN cd weschatbot/docs \
    && make html \
    && cd ../..

RUN python -m build \
    && pip install dist/weschatbot-0.0.1-py3-none-any.whl

EXPOSE 9292
EXPOSE 3000
EXPOSE 5000

CMD []