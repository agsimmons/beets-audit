from collections import Counter
import json
from pathlib import Path

from beets import library, plugins, ui


VALID_COVER_EXTENSIONS = [".jpg", ".png"]


def get_album_path(album):
    """Given an album, return the path to that album
    
    Parameters
    ----------
    album: beets.library.Album
        The album to check
    """

    # TODO: This may need to find the closest common parent path instead

    # TODO: This currently assumes utf_8 paths. Make this accept other encodings
    return Path(album.art_destination("cover.png").decode()).parent


def get_album_cover_art(album):
    """Given an album, return whether or not that album has cover art
    If no cover art is found, return None
    
    Parameters
    ----------
    album: beets.library.Album
        The album to check
    """

    for extension in VALID_COVER_EXTENSIONS:
        # TODO: This currently assumes utf_8 paths. Make this accept other encodings
        art_path = Path(album.art_destination(f"cover{extension}").decode())
        if art_path.exists():
            return art_path

    return None


def get_album_media(album):
    """Given an album, return the media type
    For example, CD or Digital
    
    Parameters
    ----------
    album: beets.library.Album
        The album to check
    """

    return Counter([item.media for item in album.items()]).most_common(1)[0][0]


class AuditPlugin(plugins.BeetsPlugin):
    def commands(self):
        cmd = ui.Subcommand("audit", help="Audit current status of music library")
        cmd.func = self.func

        return [cmd]

    def func(self, lib, opts, args):
        self._log.debug("func called")

        self.library = lib

        # TODO: Allow querying for subset of library
        query = ui.decargs(args)

        results = self.perform_audit()

        print(json.dumps(results, ensure_ascii=False))

    def perform_audit(self):
        return {
            "cover_art": self.audit_cover_art(),
            "log": self.audit_log(),
        }

    def audit_cover_art(self):
        return {
            "missing": self.audit_cover_art_missing(),
        }

    def audit_cover_art_missing(self):
        self._log.info("Checking for missing cover art...")

        results = []

        for album in self.library.albums():
            if not get_album_cover_art(album):
                results.append(str(get_album_path(album)))

        self._log.info(f"{len(results)} albums are missing cover art")

        return results

    def audit_log(self):
        return {
            "missing": self.audit_log_missing(),
        }

    def audit_log_missing(self):
        self._log.info("Checking for missing rip logs...")

        results = []

        for album in self.library.albums():
            if get_album_media(album) == "CD":
                album_path = get_album_path(album)
                disctotal = album["disctotal"]

                # TODO: This currently only checks for log files by extension.
                # .log files can be a number of different things. Maybe we should
                # try checking the log files to see if they are valid
                num_log_files = len(list(album_path.glob("**/*.log")))

                if num_log_files < disctotal:
                    results.append(
                        {
                            "path": str(album_path),
                            "disctotal": album["disctotal"],
                            "num_log_files": num_log_files,
                        }
                    )
                elif num_log_files > disctotal:
                    self._log.info(
                        f"More log files found than disctotal for an album: {album_path}"
                    )

        self._log.info(f"{len(results)} albums are missing logs")

        return results
