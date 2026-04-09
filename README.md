# myfgmMCPRepo
This repo is to build an mcp server following anthropic guidance here:
https://modelcontextprotocol.io/docs/develop/build-server

we will be building a weather server
### <u>environment set up:</u>
since we are on window using vs code letès use this command
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

```bash
# Create a new directory for our project
uv init myfgmweather
cd myfgmweather

# Create virtual environment and activate it
uv venv
.venv\Scripts\activate

# Install dependencies
uv add mcp[cli] httpx

# Create our server file
new-item myfgmweather.py
```
### <u>adding the mcp to claude</u>
open claude desktop --> settings --> develop -> edit config --> save your file

```bash
"mcpServers": {
    "myfgmweather": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "pathtoyourmcpserver\\myfgmweather.py"
      ]
    }
}
```
then 
![App Tray Menu](https://github.com/GuyFomen/myfgmMCPRepo/blob/my_sql_mcp/myfgmweather/screenshots/tray-menu.png)