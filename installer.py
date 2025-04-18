import base64
import os
from datetime import datetime

import requests

PATH = "ballsdex/packages/art"
GITHUB = "Dotsian/Art-BD-Package/contents/art"
FILES = ["__init__.py", "cog.py"]

os.makedirs(PATH, exist_ok=True)


async def add_package(package: str):
    """
    Adds a package to the config.yml file.

    Parameters
    ----------
    package: str
        The package you want to append to the config.yml file.
    """
    with open("config.yml", "r") as file:
      lines = file.readlines()

    item = f"  - {package}\n"

    if "packages:\n" not in lines or item in lines:
      return

    for i, line in enumerate(lines):
      if line.rstrip().startswith("packages:"):
          lines.insert(i + 1, item)
          break

    with open("config.yml", "w") as file:
      file.writelines(lines)

    await ctx.send("Added package to config file")


async def install_files():
    """
    Installs and updates files from the GitHub page.
    """
    for index, file in enumerate(FILES):
        request = requests.get(f"https://api.github.com/repos/{GITHUB}/{file}")

        if request.status_code != requests.codes.ok:
            await ctx.send(f"Failed to fetch {file}. `({request.status_code})`")
            break

        remote_content = base64.b64decode(request.json()["content"]).decode("UTF-8")
        local_file_path = f"{PATH}/{file}"

        with open(local_file_path, "w") as opened_file:
            opened_file.write(remote_content)

        await ctx.send(f"Updated '{file}' ({index + 1}/{len(FILES)})")

await install_files()
await add_package(PATH.replace("/", "."))

await ctx.send("Finished installing/updating everything!")