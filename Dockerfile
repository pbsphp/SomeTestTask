FROM python:2.7

RUN useradd -ms /bin/bash worker
USER worker
WORKDIR /home/worker

ENV PATH="/home/worker/.local/bin:${PATH}"

COPY --chown=worker:worker . .
RUN pip install --no-cache-dir --user -r requirements.txt && \
    pip install --no-cache-dir --user uwsgi
