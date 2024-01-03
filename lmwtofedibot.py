import sys
from time import mktime, sleep
import os
import sqlite3
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import requests
from pythorhead import Lemmy
import feedparser

import configparser

from contextlib import suppress

db_path = "/var/lib/lmwtofedibot/lmwtofedibot.sql"

if os.path.exists("./lmwtofedibot.conf"):
    conf_path = "./lmwtofedibot.conf"
elif os.path.exists("/etc/lmwtofedibot/lmwtofedibot.conf"):
    conf_path = "/etc/lmwtofedibot/lmwtofedibot.conf"

config = configparser.ConfigParser()
config.read(conf_path)

if "community" not in config["Lemmy"]:
    config["Lemmy"]["community"] = "lebensmittelwarnung"



class Warning():
    def __init__(self, title, link, description, published, warning_type):
        self.title = title
        self.link = link
        self.description = description
        self.published = published
        self.warning_type = warning_type


def post_to_lemmy(title: str, link: str, description: str, warning_type: str) -> bool:
    post_title = "[" + warning_type + "] " + title
    lemmy = Lemmy(config["Lemmy"]["instance"])
    if not lemmy.log_in(config["Lemmy"]["username"], config["Lemmy"]["password"]):
        print("[ERROR] Unable to login")
        return False
    community_id = lemmy.discover_community(config["Lemmy"]["community"])
    post = lemmy.post(
        community_id,
        post_title,
        body=description,
        url=link)

    return post


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


def get_warnings_per_api() -> list[Warning]:
    def _get_description(warning):
        if "warning" in warning:
            return warning["warning"]
        if "rapexInformation" in warning:
            return warning["rapexInformation"]["message"]

        return ""
    
    def _get_warning_type(warning) -> str:
        with suppress(KeyError):
            if warning["safetyInformation"]["ordinance"] == "Lebensmittel- und Futtermittelgesetzbuch (LFGB)":
                return "Food"
        with suppress(KeyError):
            if warning["_type"] == ".FoodWarning" and "/lebensmittel/" in warning["link"]:
                return "Food"

        return "Non-Food"

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
            "start": 0,
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
    warnings = []

    for item in response.json()["response"]["docs"]:
        warnings.append(Warning(item["title"], item["link"], _get_description(item), str(item["publishedDate"])[0:-3], _get_warning_type(item)))

    return warnings


def get_warnings_per_rss() -> list[Warning]:
    def _get_description(text: str) -> str:
        description = ""
        add_lines_to_description = False
        for line in text.splitlines():
            if line == "Betroffene Länder:":
                return description

            if add_lines_to_description:
                description += line

            if line == "Grund der Warnung:":
                add_lines_to_description = True


    def _get_warning_type(text: str) -> str:
        warning_type_dictionary = {
            "Lebensmittel": "Food",
            "kosmetische Mittel": "Non-Food",
            "Bedarfsgegenstände": "Non-Food",
            "Mittel zum Tätowieren": "Non-Food"
}
        marker_found = False
        for line in text.splitlines():
            if marker_found:
                return warning_type_dictionary.get(line, "Unknown")
            if line == "Typ:":
                marker_found = True


    feed_url = "https://www.lebensmittelwarnung.de/bvl-lmw-de/opensaga/feed/alle/alle_bundeslaender.rss"
    feed = feedparser.parse(feed_url)

    if feed.status >= 400:
        raise Exception("RSS feed returned non-success code: " + str(feed.status))

    warnings = []
    counter = 0
    for item in feed.entries:
        counter += 1
        summary_text = BeautifulSoup(item["summary"], 'html.parser').getText()
        warnings.append(Warning(item["title"], item["link"], _get_description(summary_text), str(int(mktime(item["published_parsed"]))), _get_warning_type(summary_text) ))
        if counter >= 10:
            break

    return warnings

def main():
    if not os.path.exists(db_path):
        init_db()

    try:
        print("[INFO] Getting current warnings from API...")
        warnings = get_warnings_per_api()
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
        print("[WARNING] API is broken. Trying RSS feed...")
        try:
            warnings = get_warnings_per_rss()
        except:
            warnings = []
            print("[ERROR] Neither API nor RSS feed are currently functional.")

    for warning in warnings:
        if is_post_in_db(warning.link):
            continue
        if post_to_lemmy(warning.title, warning.link, warning.description, warning.warning_type):
            print("[INFO] Uploaded post " + warning.title + ".")
            add_post_to_db(warning.title, warning.link, warning.published)
        else:
            print("[ERROR] Could not post " + warning.title + ".")
        sleep(5)


if __name__ == "__main__":
    while True:
        main()
        sleep(600)
