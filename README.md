# Chocolate BombSquad
Chocolate BombSquad (formerly named BombSquad: Vanilla Tweaks) is a modpack that 
aims to bring minor gameplay changes,
and a VARIETY of client-side and quality 
of life changes and additions, while attempting 
to keep the vanilla style.

## THERE'S RESOURCE PACKS???
Yes, indeed! BombSquad: Vanilla Tweaks has support for
changing the vanilla assets by using the unused 
extra assets folders (audio2, textures2, and meshes2).
This means you can make your own resource packs to change the game's
assets with the least of hassle, and also to mix and match 'em around.
<br><br>
However; despite this, they are quite experimental and probably won't work
for your device or could just bug out, since they have to copy and 
delete files around to achieve this. 
This also means a restart is required each time you 
change resource packs.

### Well, how do I make/use one?
To use resource packs, open the game's mod folders using the
Open Mods Folder button in advanced, and inside said folder,
there should be a resource_packs folder. Move all resource packs
you wish to use there, and voila! Support for .zip resource packs 
should also be functional, so you don't need to extract those.
<br><br>
As for making resource packs, you must create a pack.json file
formatted like this;
```json
{
	"name": "My Pack Name",
	"description": "A description of my awesome resource pack!",
	"namespace": "mypacknamespace"
}
```
Make sure the namespace is unique; it'll be used generally 
to refer to your pack.<br>
You may optionally include a pack.dds with your resource pack,
as it'll be used for the pack icon. Make sure the texture is in 1:1,
and that its' resolution is a power of 2 (so 256x256, 512x512, 1024x1024...)
Non 1:1 aspect ratio textures are supported, but they are resized
back to 1:1 in the resource packs window and anywhere else.
<br><br>
To actually replace or include assets, you must create a assets
folder in the same folder as your resource pack folder, and add
new folders according to what you will replace (eg. audio, textures, meshes).
Then, place whatever assets you will use into their respective folders.
<br>
A example pack is included in the game's files if you wish to use that as a base.
