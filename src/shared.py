from typing import Literal
import dataclasses
import colorlog
import logging
import re


EXIF_FORMATS = [
    "jpg",
    "jpeg",
    "tif",
    "tiff",
    "png",
    "webp",
    "gif",
    "bmp",
    "j2k",
    "jp2",
    "jpx",
    "jpm",
    "mj2",
    "heic",
    "heif",
    "psd",
    "dng",
    "cr2",
    "cr3",
    "nef",
    "arw",
    "orf",
    "rw2",
    "raf",
    "srw",
    "pef",
    "3fr",
    "mef",
    "mos",
    "x3f",
    "mov",
    "mp4",
    "m4v",
    "3gp",
    "3g2",
    "avi",
    "mkv",
    "mts",
    "m2ts",
    "mp3",
    "wav",
    "flac",
    "pdf",
    "eps",
    "ps",
    "svg",
    "jxl",
    "icns",
    "aai",
    "fits",
]


@dataclasses.dataclass(frozen=True)
class Attributes:
    no_exif_data: bool
    no_timestamps: bool


def create_logger(name: str) -> logging.Logger:
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter("%(log_color)s%(levelname)s - %(message)s")
    )

    logger = colorlog.getLogger(name)
    logger.addHandler(handler)

    return logger


def parse_backup_list(
    file: str,
) -> list[tuple[str, str]] | Literal["empty", "parsing_error", "file_error"]:
    try:
        with open(file, "r") as backup_list_fd:
            output = [
                tuple(line.split(":"))
                for line in backup_list_fd.read().splitlines()
                if line.count(":") == 1
            ]
    except OSError:
        return "file_error"

    for value in output:
        if len(value) != 2:
            return "parsing_error"

    if len(output) == 0:
        return "empty"

    return output  # type: ignore


def parse_ignore_list(
    file: str,
) -> list[re.Pattern[str]] | Literal["empty", "file_error"]:
    try:
        with open(file, "r") as ignore_list_fd:
            output = [
                re.compile(line)
                for line in ignore_list_fd.read().splitlines()
                if len(line) > 0
            ]
    except OSError:
        return "file_error"

    if len(output) == 0:
        return "empty"

    return output


def write_attributes_list(path: str, attributes: Attributes) -> None:
    with open(path, "w") as attributes_list_fd:
        if attributes.no_exif_data:
            attributes_list_fd.write("no_exif_data\n")
        if attributes.no_timestamps:
            attributes_list_fd.write("no_timestamps\n")


def parse_attributes_list(file: str) -> Attributes:
    with open(file, "r") as attributes_list_fd:
        attributes = [
            line.casefold().strip() for line in attributes_list_fd.read().splitlines()
        ]

    return Attributes("no_exif_data" in attributes, "no_timestamps" in attributes)
