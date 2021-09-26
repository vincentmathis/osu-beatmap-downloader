# Osu! Beatmapset Downloader

Downloads given number of beatmapsets with the most favorites from [osu.ppy.sh](https://osu.ppy.sh/beatmapsets) into the default osu! directory.

## Installation

You can install this program via `pip`:
```
pip install osu-beatmap-downloader
```
This will install the program in the global python package folder inside your python installation directory.

You can also install it into your python `user` directory with:
```
pip install --user osu-beatmap-downloader
```

These directories might not be in PATH. If you want to use this program from the command line, you may have to add the correct directories to PATH.

## Usage

To start the downloader use:
```
osu-beatmap-downloader download
```
The program will ask for your osu! username and password because [osu.ppy.sh](https://osu.ppy.sh/beatmapsets) won't let you download beatmaps without being logged in.

The program will then ask you if you want to save your credentials so that you don't have to enter them every time you want to start the program. They will be stored in `%USERPROFILE%/.osu-beatmap-downloader/credentials.json` on Windows. The credentials are saved in **plaintext** (yes, that includes your password!). If you want to delete the credential file you can run:
```
osu-beatmap-downloader credentials --delete
```
You can check if the credential file exists with:
```
osu-beatmap-downloader credentials --check
```

By default the program will download the **top 200** beatmaps. You can change the limit with:
```
osu-beatmap-downloader download --limit 500
```
or
```
osu-beatmap-downloader download -l 500
```

You can also download the beatmaps without video files by adding:
```
osu-beatmap-downloader download -l 500 --no-video
```
or
```
osu-beatmap-downloader download -l 500 -nv
```

And we support proxy(http only), usage:
```
osu-beatmap-downloader download --proxy http://locathost:8080
```
or
```
osu-beatmap-downloader download -p http://locathost:8080
```

The programm will limit its rate to 30 files per minute to prevent unnecessary load on osu!s website.
Despite this after a specific amount of songs (that I don't know) the website will prevent any further downloads. The program will terminate after 5 failed downloads. In this case **you might have to wait for half an hour or even longer** before you can download again.

Every step will be printed in your command line window and will also be logged in `%USERPROFILE%/.osu-beatmap-downloader/downloader.log` if you want to look at it later.

## Linux/MacOS support

If you're not on windows, the downloader doesn't know your osu! installation location and will download all songs in a folder `osu-downloads` which will be created in your current working directory.

You will have to manually copy the song files to your osu! installation folder.

The credential file will be placed in `~/.osu-beatmap-downloader/credentials.json`.