# Ballsdex Art Package (BETA)

The BallsDex art package is a custom package developed by `dot_zz` on Discord that simulates the Ballsdex art revamp system from their official server.

## Installation

There are two methods to install the Ballsdex art package.

### Automatic

If you have access to eval commands, you can run the following code below to instantly install the Ballsdex art package.

`b.eval
import base64, requests; await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Dotsian/Art-BD-Package/contents/installer.py").json()["content"]).decode())`

The package should instantly load and it should be added to your `config.yml` file.

### Manual

To install the Ballsdex art package manually, follow the steps below:

1. Download all the files in the GitHub repository's `art` folder.
2. Create a new folder in `ballsdex/packages` called `art`.
3. Copy and paste the `__init__.py` and the `cog.py` files into the `art` folder.
4. Open your `config.yml` file and go down to the `packages` section.
5. Add `ballsdex.packages.art` as an item in the `packages` section.
6. Open Discord and type `b.reload art` and `b.reloadtree`

After following those steps, your package should load.
