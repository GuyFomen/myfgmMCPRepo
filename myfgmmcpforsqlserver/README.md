# myfgmmcpforsqlserver
this project is to build a light mcp server for my sql DB.
in this project we will introduce the TDD concept -Test Driver Development using a Makefile

### <u>environment set up:</u>
since we are on window using vs code let's use this command
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

```bash
# Create a new directory for our project
uv init myfgm_sql_mcp_server
cd myfgm_sql_mcp_server

# Create virtual environment and activate it
uv venv
.venv\Scripts\activate

# Install dependencies
uv add mcp[cli] httpx

# Create our server file
new-item myfgm_sql_mcp_server.py
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


## Samples question to this server:

### Schema exploration
```bash
What tables do I have in my database?
Describe the dim_patient table
What columns does fact_wound_assessment have?
How are the fact tables related to the dimension tables?
```

### Data profiling
```bash
How many rows are in each table?
Which is the largest table in WoundCareDB?
How many columns does each table have?
```

### Query building — simple
```bash
Show me the first 10 patients
Show me all clinicians
Give me a count of wound assessments per patient
```


### Query building — intermediate
```bash
Show me all wound assessments joined with patient info
How many clinical visits happened per month?
Which patients had the most wound assessments?
Give me a summary of clinical visits per clinician
```

## Query building — analytical
```bash
Show me the trend of wound assessments over time
Which clinician has the highest number of patients?
Show me patients who had both a clinical visit and a wound assessment on the same date
Build me a query that shows patient activity across all fact tables
```

## Iterative query refinement
```bash
That query is too slow, can you add a TOP 100?
Can you add a WHERE clause to filter only 2024 data?
Now group that by month instead of day
Add the clinician name to those results
```