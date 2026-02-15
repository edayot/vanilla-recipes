
tag airdox_ add convention.debug

ver = str(ctx.project_version)

tellraw @a[tag=convention.debug] {"text": f"[Loaded Vanilla Recipes v{ver}]", "color": "green"}