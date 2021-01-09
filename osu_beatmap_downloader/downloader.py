import argparse
import json
import os
import re
import sys
import time

import requests
from loguru import logger
from PyInquirer import prompt

HOME_DIR = os.path.join(os.getenv("USERPROFILE"), ".osu-beatmap-downloader")
CREDS_FILEPATH = os.path.join(HOME_DIR, "credentials.json")
LOGS_FILEPATH = os.path.join(HOME_DIR, "downloader.log")
OSU_BASE_PATH = os.path.join(os.getenv("LOCALAPPDATA"), "osu!", "Songs")
ILLEGAL_CHARS = re.compile(r"[\<\>:\"\/\\\|\?*]")

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
            "sink": LOGS_FILEPATH,
            "format": " | ".join((FORMAT_TIME, FORMAT_LEVEL, FORMAT_MESSAGE)),
        },
    ]
}
logger.configure(**LOGGER_CONFIG)

OSU_URL = "https://osu.ppy.sh/home"
OSU_SESSION_URL = "https://osu.ppy.sh/session"
OSU_SEARCH_URL = "https://osu.ppy.sh/beatmapsets/search"


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
            with open(CREDS_FILEPATH, "r") as cred_file:
                self.credentials = json.load(cred_file)
        except FileNotFoundError:
            logger.info(f"File {CREDS_FILEPATH} not found")
            self.ask_credentials()

    def save_credentials(self):
        try:
            with open(CREDS_FILEPATH, "w") as cred_file:
                json.dump(self.credentials, cred_file, indent=2)
        except IOError:
            logger.error(f"Error writing {CREDS_FILEPATH}")


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
    def __init__(self, limit):
        self.beatmapsets = set()
        self.limit = limit
        self.cred_helper = CredentialHelper()
        self.cred_helper.load_credentials()
        self.session = requests.Session()
        self.login()
        self.scrape_beatmapsets()
        self.remove_existing_beatmapsets()

    def get_token(self):
        # access the osu! homepage
        homepage = self.session.get(OSU_URL)
        # extract the CSRF token sitting in one of the <meta> tags
        regex = re.compile(r".*?csrf-token.*?content=\"(.*?)\">", re.DOTALL)
        match = regex.match(homepage.text)
        csrf_token = match.group(1)
        return csrf_token

    def login(self):
        logger.info(" DOWNLOADER STARTED ".center(50, "#"))
        data = self.cred_helper.credentials
        data["_token"] = self.get_token()
        headers = {"referer": OSU_URL}
        res = self.session.post(OSU_SESSION_URL, data=data, headers=headers)
        if res.status_code != requests.codes.ok:
            logger.error("Login failed")
            sys.exit(1)
        logger.success("Login succesfull")

    def scrape_beatmapsets(self):
        fav_count = sys.maxsize
        num_beatmapsets = 0
        logger.info("Scraping beatmapsets")
        while num_beatmapsets < self.limit:
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
                tries = 0
                time.sleep(2)
            else:
                self.beatmapsets.add(next_set)
                tries += 1
                if tries > 4:
                    logger.error("Failed 5 times in a row")
                    logger.info("Website download limit reached")
                    logger.info("Try again later")
                    logger.info(" DOWNLOADER TERMINATED ".center(50, "#") + "\n")
                    sys.exit()
        logger.info(" DOWNLOADER FINISHED ".center(50, "#") + "\n")


def main():
    parser = argparse.ArgumentParser("osu-beatmap-downloader")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-l",
        "--limit",
        type=int,
        help="Maximum number of beatmapsets to download",
        default=200,
    )
    group.add_argument("--delete-creds", action="store_true")
    args = parser.parse_args()
    if args.delete_creds:
        try:
            os.remove(CREDS_FILEPATH)
            print("Credential file successfully deleted")
        except FileNotFoundError:
            print("There is no credential file to delete")
    else:
        loader = Downloader(args.limit)
        loader.run()


if __name__ == "__main__":
    main()
