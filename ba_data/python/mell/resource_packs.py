"""Classes for resource packs and helpers."""
from __future__ import annotations

import zipfile
import tempfile
import json
import shutil
import os
from pathlib import Path
from enum import Enum

def get_pack_icon(pack: ResourcePack, ui: bool = False):
    """Get a resource pack's icon texture.

    Copies its' pack.dds into the game's extra texture directory if needed,
    then returns the corresponding bs.Texture. If no icon exists, returns
    the white bs.Texture and does nothing else.
    """
    import bascenev1 as bs
    import bauiv1 as bui

    module = bui if ui else bs

    if not pack.exists('pack.dds'):
        return module.gettexture('white')

    data_dir = Path(bs.app.env.data_directory) / 'ba_data'
    icon_dir = data_dir / 'textures2' / 'pack_icons'
    icon_path = icon_dir / f'{pack.namespace}.dds'

    # if the texture's not there yet,
    # take  it from the resource pack
    if not icon_path.is_file():
        icon_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pack.get_path('pack.dds'), icon_path)

    return module.gettexture(f'pack_icons/{pack.namespace}')


def apply_resource_pack(pack: ResourcePack):
    """Copy a resource pack's assets into the 
    game's extra asset folders."""
    import babase as ba

    data_dir = Path(ba.app.env.data_directory) / 'ba_data'

    asset_folders = (
        'audio',
        'textures',
        'meshes',
    )

    for folder in asset_folders:
        source = f'assets/{folder}'
        
        if not pack.exists(source):
            continue

        source_path = pack.get_path(source)
        destination = data_dir / f'{folder}2'

        destination.mkdir(parents=True, exist_ok=True)

        for item in source_path.iterdir():
            target = destination / item.name

            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

def clear_resource_packs():
    """Clears every single resource pack asset."""
    import bascenev1 as bs
    data_dir = Path(bs.app.env.data_directory) / 'ba_data'
    asset_folders = (
        'audio2',
        'textures2',
        'meshes2',
    )
    asset_folders = list(
        data_dir / folder
        for folder in asset_folders
    )
    for folder in asset_folders:
        for item in folder.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


class PackType(Enum):
    """Enumeration that represents what type
    a resource pack uses (zip, folder...)"""
    ZIP = 'zip'
    FOLDER = 'folder'

class ResourcePack:
    """A class that represents a resource pack.
    
    A resource pack can, normally, replace assets from 
    the game without replacing it entirely, can also provide new assets, 
    and can be mixed together in a order.
    Use apply_resource_pack to apply it (and also issue a media reload.)
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)
        # Set some attributes based on 
        # what pack type we are
        if self.path.is_dir():
            self.type = PackType.FOLDER
            self.zip = None
            self.cache = None
        elif self.path.suffix.lower() in ['.zip']:
            self.type = PackType.ZIP
            self.zip = zipfile.ZipFile(self.path)
            self.cache = Path(tempfile.mkdtemp())
        else:
            raise ValueError(f'Pack is not a zip or a folder')
        # for now we don't wish to expose
        # the data directly... so keep metadata
        # type stuff as just regular strings
        data = self.read('pack.json')
        data = json.loads(data)
        self.name = data.get('name')
        self.description = data.get('description')
        self.namespace = data.get('namespace')
        self.id = id(self)
    
    def exists(self, path: str) -> bool:
        if self.type is PackType.FOLDER:
            return (
                (self.path / path).is_file() 
                or (self.path / path).is_dir()
            )

        return path in self.zip.namelist()

    def read(self, path: str) -> bytes:
        if self.type is PackType.FOLDER:
            return (self.path / path).read_bytes()

        return self.zip.read(path)

    def close(self):
        if self.zip:
            self.zip.close()
    
    def get_path(self, path: str):
        # if we're a folder, just return that path fine
        if self.type is PackType.FOLDER:
            return self.path / path
        
        # otherwise, assume we're a zip and extract contents
        output = self.cache / path
        
        if not output.exists():
            output.parent.mkdir(parents=True, exist_ok=True)
            with self.zip.open(path) as src, open(output, "wb") as dst:
                dst.write(src.read())
        
        return output