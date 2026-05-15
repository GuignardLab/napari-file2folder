from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Union

from bioio import BioImage

_SUPPORTED_SUFFIXES = {".tif", ".tiff", ".lsm", ".nd2", ".czi", ".zarr"}


def _is_supported_path(path: Union[str, Path]) -> bool:
    suffixes = [suffix.lower() for suffix in Path(path).suffixes]
    if not suffixes:
        return False
    if suffixes[-1] in _SUPPORTED_SUFFIXES:
        return True
    if len(suffixes) >= 2 and suffixes[-2:] in (
        [".ome", ".tif"],
        [".ome", ".tiff"],
        [".ome", ".zarr"],
    ):
        return True
    return False


def get_reader(
    path: Union[str, Path, Sequence[Union[str, Path]]],
) -> Optional[Callable[[Union[str, Path, Sequence[Union[str, Path]]]], list]]:

    paths: Iterable[Union[str, Path]]

    if isinstance(path, (str, Path)):
        paths = [path]
    else:
        paths = path

    paths = list(paths)
    if not paths:
        return None

    if not all(_is_supported_path(p) for p in paths):
        return None

    def _reader(paths: Union[str, Path, Sequence[Union[str, Path]]]) -> list:

        if isinstance(paths, (str, Path)):
            paths = [paths]

        layers = []

        for item in paths:
            item_path = Path(item)

            image = BioImage(str(item_path))
            data = image.dask_data

            meta = {
                "name": item_path.stem,
            }

            layers.append((data, meta, "image"))

        return layers

    return _reader


if __name__ == "__main__":
    import napari

    viewer = napari.Viewer()
    napari.run()
