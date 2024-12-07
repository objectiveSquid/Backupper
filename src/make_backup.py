from shared import (
    parse_backup_list,
    parse_ignore_list,
    create_logger,
    EXIF_FORMATS,
)

from typing import Any
import multiprocessing.pool
import subprocess
import argparse
import logging
import shutil
import time
import re
import os


SUCCESS_RETURN_CODE = 0
ARGUMENTS_ERROR_RETURN_CODE = 1


_logger = create_logger("make_backup")
_logger.setLevel(logging.INFO)


def main(
    backup_directory: str,
    backup_list_path: str,
    ignore_list_path: str | None,
    copy_exif: bool,
    copy_timestamps: bool,
    threads: int,
) -> int:
    # parsing files
    if isinstance(backup_list_path, str):
        backup_list = parse_backup_list(backup_list_path)
        if backup_list in ("empty", "parsing_error"):
            _logger.critical("Invalid backup list")
            return ARGUMENTS_ERROR_RETURN_CODE
        elif backup_list == "file_error":
            _logger.critical("Could not read backup list")
            return ARGUMENTS_ERROR_RETURN_CODE
    else:
        backup_list = backup_list_path[1]
        backup_list_path = backup_list_path[0]

    if ignore_list_path == None:
        ignore_list = []
    else:
        ignore_list = parse_ignore_list(ignore_list_path)
        if ignore_list == "empty":
            _logger.critical("Invalid ignore list")
            return ARGUMENTS_ERROR_RETURN_CODE
        elif ignore_list == "file_error":
            _logger.critical("Could not read ignore list")
            return ARGUMENTS_ERROR_RETURN_CODE

    # preperation
    target_directory = f"{backup_directory}/{int(time.time())}"
    files_directory = f"{target_directory}/files"
    meta_directory = f"{target_directory}/meta"

    # create folders
    os.makedirs(files_directory)
    os.makedirs(meta_directory)

    # meta folder
    shutil.copy2(backup_list_path, f"{meta_directory}/backups.list")
    if ignore_list_path != None:
        shutil.copy2(ignore_list_path, f"{meta_directory}/ignore.list")

    # actually copying files
    with multiprocessing.pool.ThreadPool(threads) as pool:
        for input_path, output_path in backup_list:
            if os.path.isfile(input_path):
                pool.apply_async(
                    modified_copy,
                    args=[
                        ignore_list,
                        input_path,
                        output_path,
                        copy_exif,
                        copy_timestamps,
                    ],
                )
            else:
                pool.apply_async(
                    shutil.copytree,
                    [input_path, f"{files_directory}/{output_path}"],
                    kwds={
                        "copy_function": lambda source, destination: modified_copy(
                            ignore_list, source, destination, copy_exif, copy_timestamps
                        )
                    },
                )

        pool.close()
        pool.join()

    return SUCCESS_RETURN_CODE


def modified_copy(
    ignore_list: list[re.Pattern[str]],
    source: str,
    destination: str,
    copy_exif: bool,
    copy_timestamps: bool,
) -> Any:
    for ignore_pattern in ignore_list:
        if re.match(ignore_pattern, source):
            _logger.info(f"Item {source} in ignore list ({ignore_pattern})")
            return None
    _logger.info(f"[ {round(os.stat(source).st_size / 1048576, 3) : <7} MB ] {source}")
    copy2_destination = shutil.copy2(source, destination)
    if (
        os.path.splitext(source)[1].lstrip(".").casefold() in EXIF_FORMATS and copy_exif
    ) or copy_timestamps:
        exiftool_cmd = ["exiftool", "-TagsFromFile", source]
        if copy_exif:
            exiftool_cmd.append("-All:All")
        if copy_timestamps:
            exiftool_cmd.append("-FileModifyDate")
            exiftool_cmd.append("-FileCreateDate")
        exiftool_cmd.append("-overwrite_original")
        exiftool_cmd.append(destination)

        subprocess.Popen(
            exiftool_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    return copy2_destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        os.path.split(__file__)[1], description="Create a backup"
    )

    parser.add_argument("backup_directory", help="Where to put the backup")
    parser.add_argument("backup_list", type=str, help="List of backup locations")
    parser.add_argument(
        "--ignore_list", type=str, default=None, help="List of paths to ignore"
    )
    parser.add_argument(
        "--dont_copy_exif", action="store_true", help="Do not copy EXIF data"
    )
    parser.add_argument(
        "--dont_copy_timestamps", action="store_true", help="Do not copy timestamp data"
    )
    parser.add_argument("--threads", type=int, default=1, help="Number of threads")

    args = parser.parse_args()

    if not os.path.isfile(args.backup_list):
        parser.error(f"The file {args.backup_list} does not exist")
    if not os.path.isfile(args.ignore_list) and args.ignore_list != None:
        parser.error(f"The file {args.ignore_list} does not exist")

    exit(
        main(
            args.backup_directory,
            args.backup_list,
            args.ignore_list,
            not args.dont_copy_exif,
            not args.dont_copy_timestamps,
            args.threads,
        )
    )
