#!./yt/bin/python

from pprint import pprint
from pytube import YouTube
from pytube.exceptions import VideoUnavailable
from mutagen.mp4 import MP4
# from bs4 import BeautifulSoup
import json
import sys

BASE_YOUTUBE_URL = "https://www.youtube.com/watch?v="
SAVE_DIR = "sounds/"


def get_nested(data: dict, keys: tuple):
    if len(keys) == 1:
        return data.get(keys[0])
    return get_nested(data.get(keys[0]), keys[1:])


def get_id_from_row(row):
    try:
        runs = get_nested(row, ('metadataRowRenderer', "contents"))[0]["runs"][0]
    except (KeyError, AttributeError):
        return
    title = runs.get("text")
    try:
        video_id = get_nested(runs, ("navigationEndpoint", "watchEndpoint", "videoId"))
        video_url = get_nested(
            runs, ("navigationEndpoint", "commandMetadata", "webCommandMetadata", "url"))
    except (KeyError, AttributeError):
        return
    return title, video_id, video_url


def get_mix_tracks_ids(url):
    yt = YouTube(url)
    contents_keys = ("contents", "twoColumnWatchNextResults",
                     "results", "results", "contents")
    contents = get_nested(yt.initial_data, contents_keys)

    videoSecondaryInfoRenderer = [
        i for i in contents if "videoSecondaryInfoRenderer" in i.keys()][0]["videoSecondaryInfoRenderer"]

    rows = videoSecondaryInfoRenderer["metadataRowContainer"]['metadataRowContainerRenderer']["rows"]
    rows = [get_id_from_row(r) for r in rows]
    return [r for r in rows if r]


def generate_tracklist(url):
    yt = YouTube(url)
    song_ids = get_mix_tracks_ids(url)
    data = list()
    for md in yt.metadata:
        for t in song_ids:
            if t[0] == md.get("Song"):
                data.append({
                    **md,
                    "url": t[2],
                    "id": t[1]
                })
    return data, yt.title


def set_metadata(filepath: str, metadata: dict = None):
    '''
    metadata: dict(
        title,
        artist,
        album
    )
    '''
    metadata = metadata or {}
    audio = MP4(filepath)
    itunes_md_keys_converter = {
        'title': "\xa9nam",
        "artist": "\xa9ART",
        "album": "\xa9alb",
    }
    for k, v in metadata.items():
        audio[itunes_md_keys_converter[k]] = v
    audio.save()


def download_sound(url, filename=None, output=None, metadata=None):
    yt = YouTube(url)

    try:
        sound = yt.streams.get_audio_only()
    except VideoUnavailable:
        print(f"Error downloading [{filename or url}], video unavailable")
        return
    output = output or ""
    output = SAVE_DIR + output
    filename = filename or sound.default_filename
    if sound:
        print(f'Downloading {filename} ')
        filepath = sound.download(output_path=output, filename=filename)
        if metadata:
            set_metadata(filepath, metadata=metadata)
        return filepath
    return


def main(url):
    track, mix_title = generate_tracklist(url)

    for t in track:
        video_url = BASE_YOUTUBE_URL + t["id"]
        filename = f"{t['Artist']} -- {t['Song']}"
        # filename = filename.replace('"', '').replace("'", '')
        metadata = {
            "title": t["Song"],
            "artist": t["Artist"],
            "album": mix_title,
        }
        filepath = download_sound(
            video_url, filename=filename, output=mix_title, metadata=metadata
        )
        t.update({
            "metadata": metadata,
            "filepath": filepath,
            "error": False,
        })
        if not filepath:
            t["error"] = True
            continue

    with open(f"{SAVE_DIR}/{mix_title}/download_report.json","w") as f:
        json.dump(track, f, indent=4)


if __name__ == "__main__":
    if "--url" in sys.argv:
        md_keys = ["title", "artist", "album"]
        md = {}
        for k in md_keys:
            if f"--{k}" in sys.argv:
                md[k] = sys.argv[sys.argv.index(f"--{k}") + 1]
        dl_url = sys.argv[sys.argv.index("--url") + 1]
        download_sound(dl_url, metadata=md)
        exit()

    if "--mix" in sys.argv:
        mix_url = sys.argv[sys.argv.index("--mix") + 1]
    else:
        mix_url = input('Enter mix url\n')
    main(mix_url)

"""
    "contents": {
        "twoColumnWatchNextResults": {
            "results": {
                "results": {
                    "contents": [
videoSecondaryInfoRenderer
metadataRowContainer
metadataRowContainerRenderer

row['metadataRowRenderer']["contents"][0]["runs"][0]["navigationEndpoint"]["watchEndpoint"]["videoId"]

"""
