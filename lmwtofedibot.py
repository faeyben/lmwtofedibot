import sys
from time import sleep
import os
import sqlite3
from datetime import datetime, timedelta
import requests
from pythorhead import Lemmy

import configparser

db_path = "/var/lib/lmwtofedibot/lmwtofedibot.sql"

if os.path.exists("./lmwtofedibot.conf"):
    conf_path = "./lmwtofedibot.conf"
elif os.path.exists("/etc/lmwtofedibot/lmwtofedibot.conf"):
    conf_path = "/etc/lmwtofedibot/lmwtofedibot.conf"

config = configparser.ConfigParser()
config.read(conf_path)


def post_to_lemmy(title, link, published, description):
    lemmy = Lemmy(config["Lemmy"]["instance"])
    if not lemmy.log_in(config["Lemmy"]["username"], config["Lemmy"]["password"]):
        print("[ERROR] Unable to login")
        sys.exit(1)
    community_id = lemmy.discover_community("lebensmittelwarnung")
    post = lemmy.post(
        community_id,
        title,
        body=description,
        url=link)

    if post:
        print("[INFO] Uploaded post " + title + ".")


def add_post_to_db(title, link, published):
    conn = create_connection()
    c = conn.cursor()
    c.execute("""INSERT INTO warnungen(title, link, published)
                 VALUES(?,?,?)""", (title, link, published))
    conn.commit()
    return c.lastrowid


def is_post_in_db(link):
    conn = create_connection()
    c = conn.cursor()
    c.execute("""SELECT id FROM warnungen WHERE link=?""", (link,))

    if len(c.fetchall()) > 0:
        return True
    return False


def create_connection():
    """create a database connection to the SQLite database"""
    conn = sqlite3.connect(db_path)
    return conn


def init_db():
    conn = create_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS warnungen (
        id integer PRIMARY KEY,
        title text,
        link text,
        published text);""")
    conn.close()


def get_description(warning):
    if "warning" in warning:
        return warning["warning"]
    if "rapexInformation" in warning:
        return warning["rapexInformation"]["message"]

    return ""


def main():
    if not os.path.exists(db_path):
        init_db()

    seven_days_ago = int((datetime.now() - timedelta(days=7)).timestamp())

    api_url = "https://megov.bayern.de/verbraucherschutz/baystmuv-verbraucherinfo/rest/api/warnings/merged"
    post_json = {
        "food": {
            "rows": 5,
            "sort": "publishedDate desc, title asc",
            "start": 0,
            "fq": [
                "publishedDate > " + str(seven_days_ago),
            ]
        },
        "products": {
            "rows": 5,
            "sort": "publishedDate desc, title asc",
            "start": 00,
            "fq": [
                "publishedDate > " + str(seven_days_ago),
            ]
        }
        }
    post_headers = {
        "accept": "application/json",
        "Authorization": "baystmuv-vi-1.0 os=ios, key=9d9e8972-ff15-4943-8fea-117b5a973c61",
        "Content-Type": "application/json"
    }

    response = requests.post(api_url, json=post_json, headers=post_headers)
    response.raise_for_status()

    for warning in response.json()["response"]["docs"]:
        link = warning["link"]
        title = warning["title"]
        published = str(warning["publishedDate"])[0:-3]
        description = get_description(warning)

        if is_post_in_db(link):
            continue
        add_post_to_db(title, link, published)
        post_to_lemmy(title, link, published, description)
        sleep(5)


if __name__ == "__main__":
    while True:
        main()
        sleep(600)
