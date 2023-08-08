# lmwtofedibot

Bot, der Meldungen aus der [Lebensmittelwarnung API ](https://github.com/bundesAPI/lebensmittelwarnung-api) in eine Lemmy Community posted.

## Starten

Baue zuerst das Docker Image

```
docker build -t faeyben/lmwtofedibot .
```

Kopiere dann die `lmwtofedibot.conf_example` nach `lmwtofedibot.conf` und passe sie entsprechend an.

Danach starte den Docker Container

```
docker run -d -v $(pwd)/lmwtofedibot.conf:/etc/lmwtofedibot/lmwtofedibot.conf:ro faeyben/lmwtofedibot
```