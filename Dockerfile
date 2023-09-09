FROM python:3.11

WORKDIR /lmwtofedibot
VOLUME /var/lib/lmwtofedibot

RUN useradd -m -r lmwtofedibot && \
    chown lmwtofedibot: /lmwtofedibot /var/lib/lmwtofedibot
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY lmwtofedibot.py .

CMD ["python", "-u", "lmwtofedibot.py"]