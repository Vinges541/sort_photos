import platform
import argparse
from pathlib import Path
from sys import stderr
from datetime import datetime
from PIL import Image
import PIL.ExifTags

if platform.system() != 'Windows':
    print('Only Windows systems are supported', file=stderr)
    exit(-1)

parser = argparse.ArgumentParser(
    description='File Sorting using their timestamps')
parser.add_argument('src', type=Path)
parser.add_argument('dst', type=Path)
args = parser.parse_args()

src: Path = args.src
dst: Path = args.dst

if src.is_dir() is not True:
    print('src is not a directory', file=stderr)
    exit(-2)

dirs: dict[str, Path] = {}

for item in src.rglob('*'):
    if item.is_file() is not True:
        continue

    created_at = None

    with Image.open(item) as img:
        exif = {
            PIL.ExifTags.TAGS[k]: v
            for k, v in img._getexif().items()
            if k in PIL.ExifTags.TAGS
        }
        if exif.get('DateTime') is not None:
            created_at = datetime.strptime(
                exif.get('DateTime'), '%Y:%m:%d %H:%M:%S')

    if created_at is None:
        print(f'Can not retrieve creation date from {item}')
        continue

    year, month = created_at.year, created_at.month

    key = f'{year}{month}'
    if key in dirs.keys():
        dir = dirs[key]
    else:
        dir = Path(dst, str(year), str(month))
        dir.mkdir(parents=True, exist_ok=True)
        dirs[key] = dir

    new_item = Path(dir, item.name)
    item.replace(new_item)
