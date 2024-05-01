


import requests
import json
import os
import sys
import toml

try: 
    SMITHED_TOKEN = os.environ['SMITHED_TOKEN']
except KeyError:
    try:
        with open("credentials.json", "r") as f:
            creds = json.load(f)
        SMITHED_TOKEN = creds['SMITHED_TOKEN']
    except:
        print("Missing credentials")
        exit(1)


beet = toml.load("pyproject.toml")['tool']['beet']
all_toml = toml.load("pyproject.toml")

print(beet)

# get current version using poetry version command
command = f"poetry version | cut -d' ' -f2"
CURRENT_VERSION = os.popen(command).read().strip()
print("CURRENT_VERSION: " + CURRENT_VERSION)



post_url = (
    "https://api.smithed.dev/v2/packs/"
    f'{all_toml["tool"]["poetry"]["name"]}/versions'
    f"?token={SMITHED_TOKEN}"
    f"&version={CURRENT_VERSION}"
)


download_url = (
    "https://github.com/edayot/"
    f'{all_toml["tool"]["poetry"]["name"]}/releases/download/'
    f"v{CURRENT_VERSION}/"
    f'{all_toml["tool"]["poetry"]["name"]}_{CURRENT_VERSION}_'
    "{ziptype}.zip"
)



dep = []
with open(".beet_cache/default/index.json", "r") as f:
    cache = json.load(f)["json"]

for d, v in cache["weld_deps_installed"].items():
    dep.append({"id": d, "version": v})


pack_version = {
  "name": CURRENT_VERSION,
  "downloads": {},
  "supports": beet['meta']['mc_supports'],
  "dependencies": dep,
}

if "data_pack" in beet:
    pack_version["downloads"]["datapack"] = download_url.format(ziptype="dp")
else:
    pack_version["downloads"]["datapack"] = ""
if "resource_pack" in beet:
    pack_version["downloads"]["resourcepack"] = download_url.format(ziptype="rp")
else:
    pack_version["downloads"]["resourcepack"] = ""


response = requests.post(
    url=post_url,
    headers={"Content-Type": "application/json"},
    data=json.dumps({"data": pack_version})
)

print("PACK_VERSION:")
# print indented pack_version
print(json.dumps({"pack_version": pack_version}["pack_version"], indent=4))



# print response
print("RESPONSE:")
print(response.text)


if not response.ok:
    print("Error: " + response.text)
    sys.exit(1)