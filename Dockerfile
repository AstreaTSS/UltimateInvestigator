FROM pypy:3.10

WORKDIR /app

COPY . /app

# allows git to work with the directory, making commands like /about better
RUN git config --global --add safe.directory /app

RUN pip install -r requirements.txt
RUN pypy3 -m prisma generate

CMD [ "pypy3", "main.py" ]