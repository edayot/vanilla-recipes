
from beet import Context, DataPack, Recipe
from beet.contrib.vanilla import Vanilla


NAMESPACE = "vanilla_recipes"



def beet_default(ctx: Context):
    vanilla = ctx.inject(Vanilla)
    versions = [
        "1.21.10",
        "1.21.11",
    ]
    for i, version in enumerate(versions):
        vanilla_datapack = vanilla.releases[version].data
        overlay = ctx.data.overlays[f"vanilla_recipes_{version.replace(".","_")}"]
        pack_format = ctx.data.pack_format_registry[version]
        assert isinstance(pack_format, tuple)
        overlay.pack_format = None
        overlay.min_format = pack_format
        next_index = i
        if next_index + 1 < len(versions):
            next_index+=1
        overlay.max_format = ctx.data.pack_format_registry[versions[next_index]]
        gen_overlay(overlay, vanilla_datapack)
    
    ctx.data.min_format = ctx.data.pack_format_registry[versions[0]]
    ctx.data.max_format = ctx.data.pack_format_registry[versions[-1]]


def gen_overlay(data: DataPack, vanilla: DataPack):
    for key, recipe in vanilla.recipes.items():
        print(key)
        break