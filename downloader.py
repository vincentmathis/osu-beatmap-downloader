import os
import re
import sys
import time
import json

import requests
from PyInquirer import prompt
from loguru import logger

FORMAT_TIME = "<cyan>{time:YYYY-MM-DD HH:mm:ss}</cyan>"
FORMAT_LEVEL = "<level>{level: <8}</level>"
FORMAT_MESSAGE = "<level>{message}</level>"
LOGGER_CONFIG = {
    "handlers": [
        {
            "sink": sys.stdout,
            "format": " | ".join((FORMAT_TIME, FORMAT_LEVEL, FORMAT_MESSAGE)),
        },
        {
            "sink": "downloader.log",
            "format": " | ".join((FORMAT_TIME, FORMAT_LEVEL, FORMAT_MESSAGE)),
        },
    ]
}
logger.configure(**LOGGER_CONFIG)

OSU_SESSION_URL = "https://osu.ppy.sh/session"
OSU_SEARCH_URL = "https://osu.ppy.sh/beatmapsets/search"

OSU_BASE_PATH = os.getenv("LOCALAPPDATA") + "\\osu!\\Songs"
ILLEGAL_CHARS = re.compile(r"[\<\>:\"\/\\\|\?*]")


class CredentialHelper:
    def __init__(self):
        self.credentials = {}

    def ask_credentials(self):
        questions = [
            {
                "type": "input",
                "message": "Enter your osu! username:",
                "name": "username",
            },
            {
                "type": "password",
                "message": "Enter your osu! password:",
                "name": "password",
            },
            {
                "type": "confirm",
                "message": "Remember credentials?",
                "name": "save_creds",
            },
        ]
        answers = prompt(questions)
        self.credentials["username"] = answers["username"]
        self.credentials["password"] = answers["password"]
        if answers["save_creds"]:
            self.save_credentials()

    def load_credentials(self):
        try:
            with open("credentials.json", "r") as cred_file:
                self.credentials = json.load(cred_file)
        except FileNotFoundError:
            logger.info("File credentials.json not found")
            self.ask_credentials()

    def save_credentials(self):
        try:
            with open("credentials.json", "w") as cred_file:
                json.dump(self.credentials, cred_file, indent=2)
        except IOError:
            logger.error("Error writing credentials.json")


class BeatmapSet:
    def __init__(self, data):
        self.set_id = data["id"]
        self.title = data["title"]
        self.artist = data["artist"]
        self.download_url = f"https://osu.ppy.sh/beatmapsets/{self.set_id}/download"

    def __str__(self):
        string = f"{self.set_id} {self.artist} - {self.title}"
        return ILLEGAL_CHARS.sub("_", string)


class Downloader:
    def __init__(self):
        self.beatmapsets = set()
        self.cred_helper = CredentialHelper()
        self.cred_helper.load_credentials()
        self.session = requests.Session()
        self.login()
        self.scrape_beatmapsets()
        self.remove_existing_beatmapsets()

    def login(self):
        res = self.session.post(OSU_SESSION_URL, data=self.cred_helper.credentials)
        if res.status_code != requests.codes.ok:
            logger.error("Login failed")
            sys.exit(1)
        logger.success("Login succesfull")

    def scrape_beatmapsets(self, limit=500):
        fav_count = sys.maxsize
        num_beatmapsets = 0
        logger.info("Scraping beatmapsets")
        while num_beatmapsets < limit:
            params = {
                "sort": "favourites_desc",
                "cursor[favourite_count]": fav_count,
                "cursor[_id]": 0,
            }
            response = self.session.get(OSU_SEARCH_URL, params=params)
            data = response.json()
            self.beatmapsets.update(
                (BeatmapSet(bmset) for bmset in data["beatmapsets"])
            )
            fav_count = data["beatmapsets"][-1]["favourite_count"]
            num_beatmapsets = len(self.beatmapsets)
        logger.success(f"Scraped {num_beatmapsets} beatmapsets")

    def remove_existing_beatmapsets(self):
        filtered_set = set()
        for beatmapset in self.beatmapsets:
            dir_path = os.path.join(OSU_BASE_PATH, str(beatmapset))
            file_path = dir_path + ".osz"
            if os.path.isdir(dir_path) or os.path.isfile(file_path):
                logger.info(f"Beatmapset already downloaded: {beatmapset}")
                continue
            filtered_set.add(beatmapset)
        self.beatmapsets = filtered_set

    def download_beatmapset_file(self, beatmapset):
        logger.info(f"Downloading beatmapset: {beatmapset}")
        response = self.session.get(beatmapset.download_url)
        if response.status_code == requests.codes.ok:
            logger.success(f"{response.status_code} - Download successful")
            self.write_beatmapset_file(str(beatmapset), response.content)
            return True
        else:
            logger.warning(f"{response.status_code} - Download failed")
            return False

    def write_beatmapset_file(self, filename, data):
        file_path = f"{OSU_BASE_PATH}\\{filename}.osz"
        logger.info(f"Writing file: {file_path}")
        with open(file_path, "wb") as outfile:
            outfile.write(data)
        logger.success("File write successful")

    def run(self):
        tries = 0
        while self.beatmapsets:
            next_set = self.beatmapsets.pop()
            download_success = self.download_beatmapset_file(next_set)
            if download_success:
                time.sleep(2)
            else:
                self.beatmapsets.add(next_set)
                tries += 1
                if tries > 4:
                    logger.error("Failed 5 times (server request limit reached?)")
                    logger.info("Try again later")
                    sys.exit()


def main():
    loader = Downloader()
    loader.run()


if __name__ == "__main__":
    main()
