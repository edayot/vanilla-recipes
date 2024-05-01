execute 
    if items entity @s weapon.mainhand #vanilla_recipes:dyes
    run data modify storage smithed.crafter:main root.temp.item_tag append value "#vanilla_recipes:dyes"
execute 
    if items entity @s weapon.mainhand #vanilla_recipes:shulker_boxes
    run data modify storage smithed.crafter:main root.temp.item_tag append value "#vanilla_recipes:shulker_boxes"




