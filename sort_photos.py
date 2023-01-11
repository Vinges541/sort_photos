import argparse
import hashlib
import logging
import platform
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import PIL.ExifTags
from PIL import Image


def sha256sum(filename: Path):
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        while n := f.readinto(mv):
            h.update(mv[:n])
    return h.hexdigest()


def getexif(filename: Path):
    with Image.open(filename) as img:
        raw_exif = img._getexif()
    if raw_exif is not None:
        return {
            PIL.ExifTags.TAGS[k]: v
            for k, v in raw_exif.items()
            if k in PIL.ExifTags.TAGS
        }
    return {}


if __name__ == '__main__':
    if platform.system() != 'Windows':
        logging.critical('Only Windows systems are supported')
        exit(-1)

    parser = argparse.ArgumentParser(
        description="Photos sorting using their timestamps and camera's model name")
    parser.add_argument('src', type=Path)
    parser.add_argument('dst', type=Path)
    args = parser.parse_args()

    src: Path = args.src
    dst: Path = args.dst

    if src.is_dir() is not True:
        logging.critical('src is not a directory')
        exit(-2)

    devices: dict[str, dict[str, Path]] = {}

    skipped = Path(dst, 'skipped')
    skipped.mkdir(parents=True, exist_ok=True)

    to_check = Path(dst, 'to_check')
    to_check.mkdir(parents=True, exist_ok=True)

    for item in src.glob('**/*'):
        if item.is_file() is not True:
            continue

        created_at = None
        model = None

        exif = getexif(item)

        model: str | None = exif.get('Model')
        if model is not None and model not in devices.keys():
            devices[model] = {}

        if exif.get('DateTime') is not None:
            created_at = datetime.strptime(
                exif.get('DateTime'), '%Y:%m:%d %H:%M:%S')

        if created_at is None or model is None:
            no_value_props = []

            if created_at is None:
                no_value_props.append('creation date')

            if model is None:
                no_value_props.append("camera's model")

            logging.error(
                f'Can not retrieve {", ".join(no_value_props)} from {item}. Moved to to_check')
            new_target = Path(
                to_check, f'{item.stem} ({uuid4().hex[:8]}){item.suffix}')
            item.replace(new_target)
            continue

        year, month = str(created_at.year), str(created_at.month)

        key = f'{year}{month}'
        dirs = devices[model]

        if key in dirs.keys():
            dir = dirs[key]
        else:
            dir = Path(dst, model, year, month)
            dir.mkdir(parents=True, exist_ok=True)
            dirs[key] = dir

        target = Path(dir, item.name)
        if not target.exists():
            item.replace(target)
        elif target.stat().st_size != item.stat().st_size or sha256sum(item) != sha256sum(target):
            new_target = Path(
                to_check, f'{item.stem} ({uuid4().hex[:8]}){item.suffix}')
            logging.warning(
                f'Additional check required: {new_target} (dst exists and dst and src are not equal)')
            item.replace(new_target)
        else:
            new_target = Path(
                skipped, f'{item.stem} ({uuid4().hex[:8]}){item.suffix}')
            logging.info(
                f'Moved {item} to skipped (dst exists and dst and src are equal)')
            item.replace(new_target)
