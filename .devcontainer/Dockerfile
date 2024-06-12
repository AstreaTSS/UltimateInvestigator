FROM python:3.11

WORKDIR /app

COPY . /app

# allows git to work with the directory, making commands like /about better
RUN git config --global --add safe.directory /app

RUN pip install --no-cache-dir -r requirements.txt
RUN python -m prisma generate

ENV DB_URL="postgres://postgres@localhost/postgres"

CMD [ "python", "main.py" ]