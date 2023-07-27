# lmwtofedibot

Bot, der Meldungen aus der [Lebensmittelwarnung API ](https://github.com/bundesAPI/lebensmittelwarnung-api) in eine Lemmy Community posted.

## Starten

Baue zuerst das Docker Image

```
docker build -t faeyben/lmwtofedibot .
```

Passe dann die `lmwtofedibot.conf` entsprechend an.

Danach starte den Docker Container

```
docker run -d -v $(pwd)/lmwtofedibot.conf:/etc/lmwtofedibot/lmwtofedibot.conf:ro faeyben/lmwtofedibot
```