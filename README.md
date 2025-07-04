# Ballsdex Art Package (BETA)

The BallsDex art package (v0.2) is a custom package developed by `dot_zz` on Discord that simulates the old Ballsdex art revamp system from their official server.

## Installation

There are two methods to install the Ballsdex art package.

### Automatic

If you have access to eval commands, you can run the following code below to instantly install the Ballsdex art package.

> `b.eval
import base64, requests; await ctx.invoke(bot.get_command("eval"), body=base64.b64decode(requests.get("https://api.github.com/repos/Dotsian/Art-BD-Package/contents/installer.py").json()["content"]).decode())`

The package should instantly load and it should be added to your `config.yml` file.

### Manual

To install the Ballsdex art package manually, follow the steps below:

1. Download all the files in the GitHub repository's `art` folder.
2. Create a new folder in `ballsdex/packages` called `art`.
3. Copy and paste the `__init__.py`, `cog.py`, and `config.toml` files into the `art` folder.
4. Open your `config.yml` file and go down to the `packages` section.
5. Add `ballsdex.packages.art` as an item in the `packages` section.
6. Open Discord and type `b.reload art` and `b.reloadtree`

After following those steps, your package should load. If commands don't show, refresh your Discord.

## Customization

The Ballsdex art package comes with a `config.toml` file that allows for easy customization. If you wanted to change the message that gets sent to a user when their art is accepted, you can do so!

* `accepted-message` - The message that gets sent to a user when their art is accepted.
* `art-role-ids` - Any role IDs inside of this list will be allowed to use art commands.
* `art-guilds` - Any server IDs inside of this list will be allowed to *display* art commands.
* `safe-threads` - Any thread IDs inside of this list will prevent the thread from being deleted when running the art create command.
* `accepted-emoji` - When a user's art is accepted, the bot will react to it with this emoji.
* `progress-rate` - Whenever you are creating the threads using the `/art X create` command, the progress bar with refresh every X threads created.
* `update-thread-art` - Whether you want to update the displayed art inside of a ball thread.
* `cache-threads` - Whether you want to cache threads per ForumChannel (Improves create and update time).
