
# crafting_special_firework_rocket partial
execute 
    store result score @s smithed.data 
    if entity @s[scores={smithed.data=0}] 
    if score count smithed.data matches 2 
    if data storage smithed.crafter:input {recipe: [{id: "minecraft:gunpowder", count: 2}, {id: "minecraft:paper", count: 1}]} 
    run data modify block ~ ~ ~ Items append value {
        count: 3, 
        id: "minecraft:firework_rocket", 
        Slot: 16b,
        components: {
            'minecraft:fireworks':{flight_duration:2b}
        }
    }


execute 
    store result score @s smithed.data 
    if entity @s[scores={smithed.data=0}] 
    if score count smithed.data matches 2 
    if data storage smithed.crafter:input {recipe: [{id: "minecraft:gunpowder", count: 3}, {id: "minecraft:paper", count: 1}]} 
    run data modify block ~ ~ ~ Items append value {
        count: 3, 
        id: "minecraft:firework_rocket", 
        Slot: 16b,
        components: {
            'minecraft:fireworks':{flight_duration:3b}
        }
    }


