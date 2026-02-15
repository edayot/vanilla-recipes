
from copy import deepcopy
from typing import Never, Union
from functools import cached_property
from typing import Any, Literal, Optional, Type, get_type_hints
from beet import Context, DataPack, FormatSpecifier, Function, FunctionTag, ItemTag, Recipe
from beet.contrib.vanilla import Vanilla
from beet.resources.pack_format_registry import PackFormatRegistry
from pydantic import BaseModel, RootModel, ValidationError
from nbtlib import serialize_tag, parse_nbt


from nbtlib.tag import (
    Compound,
    Int,
    List,
    String,
    Float,
    Double,
    Byte,
    Short,
    Long,
    IntArray,
    LongArray,
)
import json


NAMESPACE = "vanilla_recipes"


RecipeTypeClass: list[Type["RecipeTypeBase"]] = []


class RecipeTypeBase(BaseModel):
    type: Literal[
        "minecraft:crafting_shaped", 
        "crafting_shaped",
        "minecraft:crafting_shapeless",
        "crafting_shapeless",
        "minecraft:crafting_transmute"
        "crafting_transmute",
    ]
    __internal_count = 0
    __errors: Any

    def __init_subclass__(cls, **kwargs):
        # not in the list, not this base class and not any base class
        if (
            cls not in RecipeTypeClass
            and not cls is RecipeTypeBase
            and not cls.__name__.endswith("Base")
        ):
            RecipeTypeClass.append(cls)
        return super().__init_subclass__(**kwargs)
    
    def next_id(self):
        self.__internal_count += 1
        return self.__internal_count
    
    def format_recipe(self, recipe: str):
        return f"{NAMESPACE}:{recipe.replace(":", "_")}_{self.next_id()}"


    def to_mcfunction(self, data: DataPack, recipe: str) -> str:
        raise NotImplementedError()
    
    def export(self, data: DataPack, recipe: str):
        raise NotImplementedError()
    

class ItemResultFull(BaseModel):
    id: str
    count: Optional[int] = None
    components: Optional[dict[str, Any]] = None

    def to_result_data(self):
        nbt = Compound({
            String("id"): String(self.id),
        })
        nbt[String("count")] = Int(self.count or 1)
        if self.components:
            nbt[String("components")] = parse_nbt(json.dumps(self.components))
        nbt[String("Slot")] = Byte(16)
        return nbt
    def to_result_command(self) -> str: 
        nbt = self.to_result_data()
        return f"data modify block ~ ~ ~ Items append value {serialize_tag(nbt)}"
    

class ItemResult(RootModel[Union[ItemResultFull, str]]):
    root: Union[ItemResultFull, str]

    def to_result_full(self):
        if isinstance(self.root, ItemResultFull):
            return self.root
        return ItemResultFull(id=self.root)

    def to_result_command(self) -> str:
        return self.to_result_full().to_result_command()

class Item(RootModel):
    root: Union[str, frozenset[str]]
    
    def __hash__(self):
        return hash(self.root)
    

    def add_tag(self, data: DataPack, recipe: str, *arg: str) -> str:
        if len(arg) == 1:
            return arg[0].removeprefix("#")
        data.item_tags[recipe] = ItemTag({
            "values": [*arg]
        })
        return recipe

    def create_tag(self, data: DataPack, recipe: str, *arg: str) -> str:
        smithed_query_tag = "smithed.crafter:event/query_tags"
        function_name = f"{NAMESPACE}:query_tags"
        if not function_name in data.functions:
            data.functions[function_name] = Function()
        if not smithed_query_tag in data.function_tags:
            data.function_tags[smithed_query_tag] = FunctionTag()
        data.function_tags[smithed_query_tag].add(function_name)
        data.function_tags[smithed_query_tag].add(f"{NAMESPACE}:query_tags_special")

        tag_name = self.add_tag(data, recipe, *arg)
        func = data.functions[function_name]
        if not hasattr(func, "_meta"):
            func._meta = set()
        if not tag_name in func._meta: 
            func._meta.add(tag_name)
            command = f"""
execute 
    if items entity @s weapon.mainhand #{tag_name}
    run data modify storage smithed.crafter:main root.temp.item_tag append value "#{tag_name}"
    """
            func.append(command)

        return "#" + tag_name.removeprefix("#")

    def to_nbt_check_item(self, data: DataPack, recipe: str) -> Compound:
        if isinstance(self.root, str):
            if not self.root.startswith("#"):
                return Compound({String("id") : String(self.root)})
            else:
                return Compound({String("item_tag") : List[String]([String(self.create_tag(data, recipe, self.root))])})
        return Compound({String("item_tag") : List[String]([String(self.create_tag(data, recipe, *self.root))])})

class CraftingShapedType(RecipeTypeBase):
    type: Literal["minecraft:crafting_shaped", "crafting_shaped"]
    category: Optional[str] = None
    group: Optional[str] = None
    show_notification: Optional[bool] = None
    pattern: list[str]
    key: dict[str, Item]
    result: ItemResult

    def export(self, data: DataPack, recipe: str):
        function_name = f"{NAMESPACE}:shaped"
        if not function_name in data.functions:
            data.functions[function_name] = Function()
            smithed_tag = "smithed.crafter:event/recipes"
            if not smithed_tag in data.function_tags:
                data.function_tags[smithed_tag] = FunctionTag()
                data.function_tags[smithed_tag].add(f"{NAMESPACE}:shaped_special")
            data.function_tags[smithed_tag].add(function_name)

        content = self.to_mcfunction(data, recipe)
        data.functions[function_name].append(content)

    def to_mcfunction(self, data: DataPack, recipe: str) -> str:
        empty_line = List[Compound]([
            Compound({String("id") : String("minecraft:air"), String("Slot") : Byte(0)}),
            Compound({String("id") : String("minecraft:air"), String("Slot") : Byte(1)}),
            Compound({String("id") : String("minecraft:air"), String("Slot") : Byte(2)}),
        ])
        void_line = List[Compound]([])
        line_count = len(self.pattern)

        shaped_recipe: dict[int, List[Compound]]
        match line_count:
            case 1:
                shaped_recipe = {
                    0: deepcopy(empty_line),
                    1: deepcopy(void_line),
                    2: deepcopy(void_line),
                }
            case 2:
                shaped_recipe = {
                    0: deepcopy(empty_line),
                    1: deepcopy(empty_line),
                    2: deepcopy(void_line),
                }
            case 3:
                shaped_recipe = {
                    0: deepcopy(empty_line),
                    1: deepcopy(empty_line),
                    2: deepcopy(empty_line),
                }
            case _:
                raise NotImplementedError(f"Recipe with {line_count} lines is not supported")
                                          
        for i, line in enumerate(self.pattern):
            for j, char in enumerate(line):
                if char == " ":
                    continue
                item = self.key[char]
                nbt = item.to_nbt_check_item(data, self.format_recipe(recipe))
                nbt[String("Slot")] = Byte(j)
                shaped_recipe[i][j] = nbt

        return f"""
execute 
    store result score @s smithed.data
    if entity @s[scores={{smithed.data=0}}]
{
    "\n".join([
        f"\tif data storage smithed.crafter:input recipe{{{serialize_tag(String(i))}: {serialize_tag(shaped_recipe[i])} }}"
        for i in shaped_recipe.keys()
    ])
}
    run {self.result.to_result_command()}

"""



class CraftingShapelessType(RecipeTypeBase): 
    type: Literal["minecraft:crafting_shapeless", "crafting_shapeless"]
    category: Optional[str] = None
    group: Optional[str] = None
    ingredients: list[Item]
    result: ItemResult

    def export(self, data: DataPack, recipe: str):
        function_name = f"{NAMESPACE}:shapeless"
        if not function_name in data.functions:
            data.functions[function_name] = Function()
            smithed_tag = "smithed.crafter:event/shapeless_recipes"
            if not smithed_tag in data.function_tags:
                data.function_tags[smithed_tag] = FunctionTag()
                data.function_tags[smithed_tag].add(f"{NAMESPACE}:shapeless_special")
            data.function_tags[smithed_tag].add(function_name)
        
        content = self.to_mcfunction(data, recipe)
        data.functions[function_name].append(content)

    def to_mcfunction(self, data: DataPack, recipe: str) -> str:
        assert 1 <= len(self.ingredients) <= 9
        counts = {ingr: 0 for ingr in self.ingredients}
        for ingr in self.ingredients:
            counts[ingr]+=1

        shapeless_recipe = List[Compound]()

        for ingr, count in counts.items():
            nbt = ingr.to_nbt_check_item(data, self.format_recipe(recipe))
            nbt[String("count")] = Int(count)
            shapeless_recipe.append(nbt)

        return f"""
execute 
    store result score @s smithed.data 
    if entity @s[scores={{smithed.data=0}}] 
    if score count smithed.data matches {len(counts)}
    if data storage smithed.crafter:input {{recipe:{serialize_tag(shapeless_recipe)}}}
    run {self.result.to_result_command()}
"""

class CraftingTransmute(RecipeTypeBase):
    type: Literal["minecraft:crafting_transmute", "crafting_transmute"]
    category: Optional[str] = None
    group: Optional[str] = None
    input: Item
    material: Item
    result: ItemResult

    def export(self, data: DataPack, recipe: str):
        function_name = f"{NAMESPACE}:shapeless"
        if not function_name in data.functions:
            data.functions[function_name] = Function()
            smithed_tag = "smithed.crafter:event/shapeless_recipes"
            if not smithed_tag in data.function_tags:
                data.function_tags[smithed_tag] = FunctionTag()
                data.function_tags[smithed_tag].add(f"{NAMESPACE}:shapeless_special")
            data.function_tags[smithed_tag].add(function_name)
        
        content = self.to_mcfunction(data, recipe)
        data.functions[function_name].append(content)

    def to_mcfunction(self, data: DataPack, recipe: str) -> str:
        shapeless_recipe = List[Compound]()
        input = self.input.to_nbt_check_item(data, self.format_recipe(recipe))
        input[String("count")] = Int(1)

        material = self.material.to_nbt_check_item(data, self.format_recipe(recipe))
        material[String("count")] = Int(1)
        

        shapeless_recipe.append(input)
        shapeless_recipe.append(material)
        return f"""
execute 
    if entity @s[scores={{smithed.data=0}}] 
    if score count smithed.data matches 2
    if data storage smithed.crafter:input {{recipe:{serialize_tag(shapeless_recipe)}}}
    run function ~/{recipe.replace(":", "_")}:
        data remove storage vanilla_recipes:main item_out
        data modify storage vanilla_recipes:main item_out set from storage smithed.crafter:input recipe[{serialize_tag(input)}]
        data modify storage vanilla_recipes:main item_out.id set value "{self.result.to_result_full().to_result_data()[String("id")]}"
        data modify storage vanilla_recipes:main item_out.Slot set value 16b
        
        data modify block ~ ~ ~ Items append from storage vanilla_recipes:main item_out
        scoreboard players set @s smithed.data 1 


"""


def parse_recipe(data: Any) -> RecipeTypeBase | None:
    if "type" not in data:
        raise ValueError(f"{data} does not contain a type key")
    value = data["type"]
    for cls in reversed(RecipeTypeClass):
        annotation = cls.model_fields["type"].annotation
        if value in annotation.__args__:
            return cls.model_validate(data)
    return None

def previous(version: FormatSpecifier):
    if isinstance(version, int):
        return (version - 1, 999)
    if len(version) == 1:
        return (version[0] - 1, 999)
    if version[1] == 0:
        return (version[0] - 1, 999)
    return (version[0], version[1] - 1)


def get_pack_format(ctx: Context, version: str):
    data = PackFormatRegistry.model_validate_json(ctx.cache[NAMESPACE].download(f"https://raw.githubusercontent.com/misode/mcmeta/refs/tags/{version}-summary/version.json").read_text())
    return (data.data_pack_version, data.data_pack_version_minor)




def beet_default(ctx: Context):
    vanilla = ctx.inject(Vanilla)
    versions = ctx.meta["mc_supports"]
    for i, version in enumerate(versions):
        print(version)
        vanilla_datapack = vanilla.releases[version].data
        overlay = ctx.data.overlays[f"vanilla_recipes_{version.replace(".","_")}"]
        pack_format = get_pack_format(ctx, version)
        overlay.pack_format = None
        overlay.min_format = pack_format
        if i + 1 < len(versions):
            overlay.max_format = previous(get_pack_format(ctx, versions[i+1]))
        else:
            overlay.max_format = pack_format
        gen_overlay(overlay, vanilla_datapack)
    
    ctx.data.min_format = get_pack_format(ctx, versions[0])
    ctx.data.max_format = get_pack_format(ctx, versions[-1])
    
    print("ending pipeline")

def gen_overlay(data: DataPack, vanilla: DataPack):
    for key, recipe in vanilla.recipes.items():
        r = parse_recipe(recipe.data)
        if not r: continue
        r.export(data, key)
