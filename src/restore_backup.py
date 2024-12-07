from shared import parse_attributes_list, parse_backup_list, create_logger, EXIF_FORMATS

from typing import Any
import multiprocessing.pool
import subprocess
import argparse
import logging
import shutil
import os


SUCCESS_RETURN_CODE = 0
INVALID_BACKUP_RETURN_CODE = 1


_logger = create_logger("restore_backup")
_logger.setLevel(logging.INFO)


def flip_backup_list(
    prepend_path: str, backup_list: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    output = []

    for item in backup_list:
        output.append((f"{prepend_path}/{item[1]}", item[0].removeprefix(prepend_path)))

    return output


def main(
    backup_directory: str, copy_exif: bool, copy_timestamp: bool, threads: int
) -> int:
    # preperation
    files_directory = f"{backup_directory}/files"
    meta_directory = f"{backup_directory}/meta"

    # parsing files
    original_backup_list = parse_backup_list(f"{meta_directory}/backups.list")
    if original_backup_list in ("empty", "parsing_error"):
        _logger.critical("Invalid backup list")
        return INVALID_BACKUP_RETURN_CODE
    elif original_backup_list == "file_error":
        _logger.critical("Could not read backup list")
        return INVALID_BACKUP_RETURN_CODE
    flipped_backup_list = flip_backup_list(files_directory, original_backup_list)

    attributes = parse_attributes_list(f"{meta_directory}/attributes.list")

    # actually copying files
    with multiprocessing.pool.ThreadPool(threads) as pool:
        for input_path, output_path in flipped_backup_list:
            if os.path.isfile(input_path):
                pool.apply_async(
                    modified_copy,
                    [
                        input_path,
                        output_path,
                        copy_exif and not attributes.no_exif_data,
                        copy_timestamp and not attributes.no_timestamps,
                    ],
                )
            else:
                pool.apply_async(
                    shutil.copytree,
                    [input_path, output_path],
                    {
                        "copy_function": lambda source, destination: modified_copy(
                            source,
                            destination,
                            copy_exif and not attributes.no_exif_data,
                            copy_timestamp and not attributes.no_timestamps,
                        ),
                        "dirs_exist_ok": True,
                    },
                )

        pool.close()
        pool.join()

    return SUCCESS_RETURN_CODE


def modified_copy(
    source: str, destination: str, copy_exif: bool, copy_timestamp: bool
) -> Any:
    _logger.info(f"[ {round(os.stat(source).st_size / 1048576, 3) : <7} MB ] {source}")
    copy2_destination = shutil.copy2(source, destination)
    if (
        os.path.splitext(source)[1].lstrip(".").casefold() in EXIF_FORMATS and copy_exif
    ) or copy_timestamp:
        exiftool_cmd = ["exiftool", "-TagsFromFile", source]
        if copy_exif:
            exiftool_cmd.append("-All:All")
        if copy_timestamp:
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
        os.path.split(__file__)[1],
        description="Restores a backup created with make_backup.py",
    )

    parser.add_argument("backup_directory", type=str, help="Path to an existing backup")
    parser.add_argument(
        "--dont_copy_exif", action="store_true", help="Do not copy EXIF data"
    )
    parser.add_argument(
        "--dont_copy_timestamp", action="store_true", help="Do not copy timestamp data"
    )
    parser.add_argument("--threads", type=int, default=1, help="Number of threads")

    args = parser.parse_args()

    if not os.path.isdir(args.target):
        parser.error(f"The path {args.backup_directory} does not exist")

    exit(
        main(
            args.backup_directory,
            not args.dont_copy_exif,
            not args.dont_copy_timestamp,
            args.threads,
        )
    )
