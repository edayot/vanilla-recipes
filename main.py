
from beet import Context, Function, Recipe, ItemTag, FunctionTag, Predicate
from beet.contrib.vanilla import Vanilla

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
from nbtlib import serialize_tag, parse_nbt

from copy import deepcopy
import json



MINECRAFT_VERSION = "1.20.6"
NAMESPACE = "vanilla_recipes"



def beet_default(ctx: Context):
    ctx.inject(Vanilla)

    mc_version = ctx.meta.get(NAMESPACE, {}).get("mc_version", MINECRAFT_VERSION)

    recipes = ctx.inject(Vanilla).releases[mc_version].data.recipes
    for recipe in recipes:
        transform_recipes(ctx, recipes[recipe], recipe)

    


def get_result_command(result: dict[str,str]):
    nbt = parse_nbt(json.dumps(result))
    nbt[String("Slot")] = Byte(16)
    return f"data modify block ~ ~ ~ Items append value {serialize_tag(nbt)}"




def transform_recipes(ctx: Context, recipe: Recipe, recipe_name: str):
    match recipe.data["type"]:
        case "minecraft:crafting_shaped":
            transform_shaped(ctx, recipe, recipe_name)
        case "minecraft:crafting_shapeless":
            transform_shapeless(ctx, recipe, recipe_name)


def parse_item_list(ctx: Context, item: list[dict], tag_name: str):
    # create a new item tag
    item_list = []
    for it in item:
        if "item" in it:
            item_list.append(it["item"])
        elif "tag" in it:
            item_list.append(f"#{it['tag']}")
        else:
            raise NotImplementedError("Unknown item format")
    ctx.data.item_tags[tag_name] = ItemTag({
        "values": item_list
    })
    item = {"tag": tag_name}

    smithed_query_tag = "smithed.crafter:event/query_tags"
    function_name = f"{NAMESPACE}:query_tags"
    if not function_name in ctx.data.functions:
        ctx.data.functions[function_name] = Function()
        if not smithed_query_tag in ctx.data.function_tags:
            ctx.data.function_tags[smithed_query_tag] = FunctionTag()
        ctx.data.function_tags[smithed_query_tag].add(function_name)
    
    ctx.data.predicates[tag_name] = Predicate({
        "condition": "minecraft:entity_properties",
        "entity": "this",
        "predicate": {
            "equipment": {
                "mainhand": {
                    "items": "#"+tag_name
                }
            }
        }
    }
    )

    command = f"""
execute 
    if predicate {tag_name}
    run data modify storage smithed.crafter:main root.temp.item_tag append value "#{tag_name}"
"""
    ctx.data.functions[function_name].append(command)


    return item
    




def transform_shaped(ctx: Context, recipe: Recipe, recipe_name: str):
    line_count = len(recipe.data["pattern"])

    void_line = List[Compound]([
        Compound({String("id") : String("minecraft:air"), String("Slot") : Byte(0)}),
        Compound({String("id") : String("minecraft:air"), String("Slot") : Byte(1)}),
        Compound({String("id") : String("minecraft:air"), String("Slot") : Byte(2)}),
    ])

    match line_count:
        case 1:
            shaped_recipe = Compound({
                String("0") : deepcopy(void_line),
            })
            void_lines = "\n\tif data storage smithed.crafter:input {recipe:{1:[]}}"
            void_lines += "\n\tif data storage smithed.crafter:input {recipe:{2:[]}}"
        case 2:
            shaped_recipe = Compound({
                String("0") : deepcopy(void_line),
                String("1") : deepcopy(void_line),
            })
            void_lines = "\n\tif data storage smithed.crafter:input {recipe:{2:[]}}"
        case 3:
            shaped_recipe = Compound({
                String("0") : deepcopy(void_line),
                String("1") : deepcopy(void_line),
                String("2") : deepcopy(void_line),
            })
            void_lines = ""
        case _:
            raise NotImplementedError(f"Recipe with {line_count} lines is not supported")
    
    for i, line in enumerate(recipe.data["pattern"]):
        for j, char in enumerate(line):
            if char == " ":
                # it's an empty slot
                continue
            item : dict[str,str] | list[dict[str,str]] = recipe.data["key"][char]
            if isinstance(item, list):
                # create a new item tag
                tag_name = f"{NAMESPACE}:recipes/{recipe_name.replace(':','/')}/{i}/{j}"
                item = parse_item_list(ctx, item, tag_name)
            if "item" in item:
                item_id = item["item"]
                shaped_recipe[str(i)][j]["id"] = String(item_id)
            elif "tag" in item:
                tag = f'#{item["tag"]}'
                del shaped_recipe[str(i)][j]["id"]
                shaped_recipe[str(i)][j]["item_tag"] = List[String]([String(tag)])
            else:
                raise NotImplementedError("Unknown item format")
            
    
    result_command = get_result_command(recipe.data["result"])


    function_name = f"{NAMESPACE}:shaped"
    if not function_name in ctx.data.functions:
        ctx.data.functions[function_name] = Function()
        smithed_tag = "smithed.crafter:event/recipes"
        if not smithed_tag in ctx.data.function_tags:
            ctx.data.function_tags[smithed_tag] = FunctionTag()
        ctx.data.function_tags[smithed_tag].add(function_name)

    command = f"""
execute 
    store result score @s smithed.data
    if entity @s[scores={{smithed.data=0}}]
    if data storage smithed.crafter:input recipe{serialize_tag(shaped_recipe)} {void_lines}
    run {result_command}

"""
    ctx.data.functions[function_name].append(command)


def transform_shapeless(ctx: Context, recipe: Recipe, recipe_name: str):
    ingredients = recipe.data["ingredients"]

    ingredients_map= []

    for i, ingredient in enumerate(ingredients):

        ingredient_in_map = False
        index_ingredient = -1
        for j, item in enumerate(ingredients_map):
            if item["ingredient"] == ingredient:
                ingredient_in_map = True
                index_ingredient = j
                break
        if ingredient_in_map:
            ingredients_map[index_ingredient]["count"] += 1
        else:
            ingredients_map.append({
                "ingredient": ingredient,
                "count": 1
            })

    shapeless_recipe = List[Compound]()
    
    for i, item in enumerate(ingredients_map):
        ingredient = item["ingredient"]
        if isinstance(ingredient, list):
            # create a new item tag
            tag_name = f"{NAMESPACE}:recipes/{recipe_name.replace(':','/')}/{i}"
            ingredient = parse_item_list(ctx, ingredient, tag_name)
        
        if "item" in ingredient:
            item_id = ingredient["item"]
            shapeless_recipe.append(Compound({
                "id": String(item_id),
                "count": Int(item["count"]),
            }))
        elif "tag" in ingredient:
            tag = f'#{ingredient["tag"]}'
            shapeless_recipe.append(Compound({
                "item_tag": List[String]([String(tag)]),
                "count": Int(item["count"]),
            })
            )
        else:
            raise NotImplementedError("Unknown item format")

    result_command = get_result_command(recipe.data["result"])

    function_name = f"{NAMESPACE}:shapeless"
    if not function_name in ctx.data.functions:
        ctx.data.functions[function_name] = Function()
        smithed_tag = "smithed.crafter:event/shapeless_recipes"
        if not smithed_tag in ctx.data.function_tags:
            ctx.data.function_tags[smithed_tag] = FunctionTag()
        ctx.data.function_tags[smithed_tag].add(function_name)

    command = f"""
execute 
    store result score @s smithed.data 
    if entity @s[scores={{smithed.data=0}}] 
    if score count smithed.data matches {len(ingredients_map)}
    if data storage smithed.crafter:input {{recipe:{serialize_tag(shapeless_recipe)}}}
    run {result_command}
"""
    
    ctx.data.functions[function_name].append(command)