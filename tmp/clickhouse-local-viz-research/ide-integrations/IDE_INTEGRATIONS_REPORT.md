# IDE Integrations for ClickHouse - Research Report

**Research Date:** 2025-11-17
**Scope:** Development environment integrations for ClickHouse database

## Executive Summary

ClickHouse has mature support across major development environments, with JetBrains tools (DataGrip, PyCharm) providing the most comprehensive native integration. VSCode has multiple extension options with varying feature sets. Jupyter notebook integration is production-ready through JupySQL. Traditional text editors (Vim, Sublime Text) have minimal ClickHouse-specific support, while Emacs has a dedicated (but archived) plugin.

---

## VSCode Extensions

### 1. SQLTools ClickHouse Driver (RECOMMENDED)

**Publisher:** ultram4rine  
**Extension ID:** `ultram4rine.sqltools-clickhouse-driver`  
**Install:** `code --install-extension ultram4rine.sqltools-clickhouse-driver`

#### Stats
- **Downloads:** 47,273
- **Rating:** 3.5/5 (2 reviews)
- **Last Updated:** November 17, 2025
- **Version:** 0.10.0
- **License:** Free/Open Source

#### Features
- Explore tables and views
- Run SQL queries with results display
- Auto-completion for ClickHouse keywords
- Syntax highlighting
- Integration with SQLTools ecosystem

#### Requirements
- SQLTools extension (dependency)
- VS Code 1.42.0+
- ClickHouse server 24.8+

#### Limitations
- **No FORMAT clause** - driver automatically applies JSON formatting
- **Single query execution only** - cannot run multiple queries at once
- Older ClickHouse versions may work but lack keyword completion

#### Pros
- Most actively maintained ClickHouse extension for VSCode
- Part of popular SQLTools ecosystem
- Cross-platform support

#### Cons
- Limited reviews/feedback
- Single query limitation may hinder workflow
- Requires understanding of SQLTools architecture

---

### 2. Clickhouse Support (Extension Pack)

**Publisher:** LinJun (Extension Studio)  
**Extension ID:** `LinJun.clickhouse-support`  
**Install:** `code --install-extension LinJun.clickhouse-support`

#### Stats
- **Downloads:** 3,484
- **Rating:** 5/5 (1 review)
- **Last Updated:** June 4, 2025
- **Version:** 1.0.6

#### Features
- Database Explorer panel with connection configuration
- Support for ClickHouse connections
- SQLite file support
- Works on Web, Linux, macOS, Windows

#### Dependencies
Bundles two extensions:
- `cweijan.vscode-database-client2` (Database Client)
- `cweijan.dbclient-jdbc` (JDBC driver support)

#### Pros
- Extension pack - easier setup
- High rating (though limited sample)
- Multi-platform including web

#### Cons
- Lower download count suggests less adoption
- Limited documentation
- Unclear feature differentiation from base Database Client

---

### 3. Database Client

**Publisher:** cweijan  
**Extension ID:** `cweijan.vscode-database-client2`

#### Features
- Multi-database support (MySQL, PostgreSQL, Redis, ClickHouse, etc.)
- SQL editor with syntax highlighting
- Schema browser
- Data preview and export
- Query history

#### ClickHouse-Specific Features
- Connect via HTTP/HTTPS
- Browse ClickHouse schemas
- Execute queries with result visualization
- Export query results

#### Notes
- Bundled in "Clickhouse Support" extension pack
- General-purpose database tool, not ClickHouse-specific

---

### 4. DBCode

**Website:** https://dbcode.io  
**Type:** Commercial VSCode extension

#### Features
- SQL query editor with ClickHouse syntax highlighting
- Data exploration with quick sample viewing
- Schema browsing
- Query results viewing and export
- Database operations (create/edit/rename/truncate/drop tables)
- Query history
- Execution plans
- Data visualization
- AI-powered copilot tools

#### Connection Setup
1. Open DBCode extension
2. Click "Add Connection" → Select ClickHouse
3. Enter: host, port (8123), username, password, database
4. Save to connect

#### Pros
- Comprehensive feature set
- Modern UI
- AI copilot integration

#### Cons
- Commercial product (pricing unclear)
- Less community adoption than open-source alternatives

---

### 5. ClickHouseLight

**Publisher:** fanruten  
**Repository:** https://github.com/fanruten/ClickHouseLight

#### Features
- Credentials stored in `.clickhouse_settings` file (workspace root)
- Basic query execution

#### Status
- Limited information available
- Appears less actively maintained
- Minimal marketplace presence

---

### 6. Clickhouse Query Formatter

**Publisher:** JoshFerge  
**Extension ID:** `JoshFerge.clickhouse-query-formatter`

#### Features
- Formats ClickHouse queries
- Syntax-aware formatting

#### Use Case
- Utility extension for query formatting
- Complements other database extensions

---

## JetBrains Tools

### DataGrip (RECOMMENDED for Database-Focused Work)

**Product:** Standalone database IDE  
**Pricing:** Paid (subscription-based)  
**Documentation:** https://clickhouse.com/docs/integrations/datagrip

#### Setup
1. Open Data Sources and Drivers dialog
2. Select ClickHouse from Complete Support list
3. Choose "Latest stable driver" from Provided Driver
4. DataGrip auto-downloads JDBC driver
5. Configure connection parameters

#### Connection Parameters
- **Host:** hostname (no protocol prefix)
- **Port:** 8123 (HTTP) or 8443 (HTTPS/Cloud)
- **Authentication:** User & Password OR No auth
- **Database:** database name

#### JDBC URL Format
```
jdbc:clickhouse://<host>:<port>/<database>
```

#### Cloud Connection (CRITICAL)
**ClickHouse Cloud REQUIRES SSL:**
```
jdbc:clickhouse://your-host.clickhouse.cloud:8443/default?ssl=true
```
Omitting `?ssl=true` causes "Connection reset" errors.

#### Features
- Browse tables, views, table data
- Run queries with full SQL editor
- **Very fast code completion**
- ClickHouse syntax highlighting
- Support for ClickHouse-specific features:
  - Nested columns
  - Table engines
  - ClickHouse functions
- Data Editor
- Refactorings
- Search and Navigation tools
- Enum value completion in data editor
- Type deduction for map literals

#### Limitations
- Cannot export data
- Cannot modify tables (DDL limitations)
- Manual driver installation required

#### Pros
- Most comprehensive ClickHouse IDE integration
- Native ClickHouse dialect support
- Professional-grade features
- Actively maintained by JetBrains

#### Cons
- Paid product (subscription required)
- Standalone app (not integrated with code editor)
- Driver not pre-shipped (manual download)

#### First Released
- Version 2018.2.2 (August 2018)
- Continuous updates through 2025

---

### PyCharm Professional

**Product:** Python IDE with database tools  
**Pricing:** Paid (subscription-based)  
**Note:** Database Tools plugin available only in PyCharm Pro

#### Features
Same database integration as DataGrip (embedded):
- ClickHouse connection support
- SQL editor with ClickHouse syntax
- Code completion and navigation
- Data viewing and editing

#### Connection Setup
1. Database tool window → New → Data Source → ClickHouse
2. Enter port (default 8123)
3. Choose authentication: User & Password OR No auth
4. Test connection

#### Use Case
Ideal for Python developers who:
- Need both Python IDE and database tools
- Already have PyCharm Pro license
- Want integrated workflow

#### Pros
- Integrated with Python development
- Same DataGrip engine
- Single IDE for code + data

#### Cons
- Requires Pro version (not Community)
- Same limitations as DataGrip for ClickHouse

---

### IntelliJ IDEA Ultimate

**Product:** Java/JVM IDE with database tools  
**Pricing:** Paid (subscription-based)

#### Features
- Same embedded DataGrip functionality
- ClickHouse connection support
- Full SQL editor with ClickHouse dialect

#### Use Case
For Java/Kotlin/Scala developers needing ClickHouse access

---

## Jupyter Notebook Integration

### JupySQL (formerly ipython-sql) (RECOMMENDED)

**Documentation:** https://clickhouse.com/docs/integrations/jupysql  
**PyPI:** `jupysql`, `clickhouse-sqlalchemy`  
**Status:** Production-ready, community-maintained

#### Installation
```bash
pip install jupysql clickhouse-sqlalchemy
```

Or in notebook:
```python
%pip install --quiet jupysql clickhouse-sqlalchemy
```

#### Setup
```python
%load_ext sql
%config SqlMagic.autocommit=False
```

#### Connection String Format
```
clickhouse://user:password@host:port/database
```

**Example (local):**
```
clickhouse://default:@localhost:8123/default
```

#### Usage Examples

**SQL Magic (inline):**
```python
%sql SELECT count() FROM my_table
```

**SQL Cell:**
```python
%%sql
SELECT 
    toDate(trip_date) as date,
    avg(trip_distance) as avg_distance
FROM trips
WHERE trip_date >= '2023-01-01'
GROUP BY date
ORDER BY date
```

**DataFrame Conversion:**
```python
result = %sql SELECT * FROM my_table
df = result.DataFrame()
```

#### Features
- Execute SQL queries with `%sql` and `%%sql` magic commands
- SQL plotting functionality:
  - Histogram generation with customizable bins
  - Grid overlays and axis labeling
- DataFrame conversion for pandas integration
- Support for complex queries:
  - Table creation with schema definitions
  - Data insertion from S3 sources
  - Aggregations (COUNT, AVG, GROUP BY)
  - Date-based filtering
  - Window functions

#### Limitations
- Community-maintained (limited official ClickHouse support)
- Relies on clickhouse_sqlalchemy driver
- Historical issue: some versions added `COMMIT` after queries (violates ClickHouse API)

#### Pros
- Native Jupyter integration
- Familiar magic command syntax
- Visualization support
- Pandas/DataFrame workflow

#### Cons
- Requires clickhouse-sqlalchemy layer
- Community support only
- Past compatibility issues

---

### Alternative: Direct Python Drivers in Notebooks

#### clickhouse-connect (Official)
```python
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='HOSTNAME.clickhouse.cloud',
    port=8443,
    username='default',
    password='password'
)

# Query to DataFrame
df = client.query_df("SELECT * FROM my_table")

# Insert DataFrame
client.insert_df('my_table', df)
```

**Features:**
- Official ClickHouse Python driver
- Native pandas integration via `query_df()` and `insert_df()`
- Support for: Pandas (numpy/arrow-backed), NumPy, PyArrow, Polars
- HTTP interface (max compatibility)
- Python 3.9+ required

**Pros:**
- Official support
- High performance
- Direct DataFrame support
- No SQLAlchemy layer

**Cons:**
- No SQL magic commands
- Imperative code (not declarative SQL)
- Different workflow than JupySQL

---

#### clickhouse-driver (Community)
```python
from clickhouse_driver import Client

client = Client(host='localhost')
result = client.execute('SELECT * FROM my_table')
```

**Features:**
- Native protocol (TCP)
- Faster than HTTP for large datasets
- NumPy/Pandas compatibility via `query_dataframe()`

**Use Case:**
- High-performance scenarios
- Large data transfers

---

### JetBrains DataSpell

**Product:** Data Science IDE  
**Documentation:** https://www.jetbrains.com/help/dataspell/clickhouse.html

#### Features
- Jupyter notebook support
- Embedded DataGrip database tools
- ClickHouse connection support
- SQL cells with ClickHouse syntax

#### Use Case
For data scientists wanting integrated notebook + database IDE

---

## Traditional Text Editors

### Emacs

#### sql-clickhouse (Archived)

**Repository:** https://github.com/rschwarz/sql-clickhouse  
**Status:** ARCHIVED (Feb 25, 2025) - Read-only  
**License:** MIT  
**Language:** Emacs Lisp

#### Features
- Adds ClickHouse as product type to built-in `sql-mode`
- Syntax highlighting for ClickHouse SQL
- Database communication via `clickhouse-client` CLI
- Uses Emacs `comint` interface for CLI interaction

#### Installation
Available on MELPA:
```elisp
(use-package sql-clickhouse
  :ensure t)
```

#### Configuration
**Important:** CLI produces status updates every 100ms in comint, causing accumulation. Workaround:
```sql
SET interactive_delay = 10000000;  -- Update every 10 seconds
```

#### Repository Stats
- **Stars:** 6
- **Forks:** 5
- **Commits:** 29
- **Files:** 4 (sql-clickhouse.el, README.org, LICENSE, .gitignore)

#### Pros
- Native Emacs integration
- Uses built-in sql-mode
- MELPA distribution

#### Cons
- **ARCHIVED** - No longer maintained
- Verbose CLI output in comint
- Requires manual workaround for output flooding
- Limited community adoption

#### Alternative
Use generic SQL mode with ClickHouse CLI via Emacs shell/terminal buffers.

---

### Vim/Neovim

**Status:** No dedicated ClickHouse plugin found

#### Current Support
- ClickHouse CLI client allows opening queries in editor via `Alt+Shift+E`
- Default editor: vim (configurable via `$EDITOR` environment variable)
- Generic SQL syntax highlighting available

#### Workarounds
1. **Generic SQL Syntax:**
   ```vim
   :set filetype=sql
   ```

2. **ClickHouse CLI Integration:**
   ```bash
   export EDITOR=nvim
   clickhouse-client
   # In client: Alt+Shift+E to edit query
   ```

3. **LSP Options:**
   - Generic SQL language servers (sqls, sql-language-server)
   - Limited ClickHouse dialect support

#### Community Interest
GitHub issue #56637 requests ClickHouse LSP with:
- Auto-complete
- Error checking
- Documentation on hover

**Status:** Feature request (Nov 2023), no implementation yet

#### Recommendation
Use generic SQL syntax highlighting + ClickHouse CLI workflow. For advanced features, consider VSCode or JetBrains tools.

---

### Sublime Text

**Status:** No dedicated ClickHouse plugin found

#### Current Support
- Generic SQL syntax highlighting
- SQLTools package (generic SQL client)
- No ClickHouse-specific extensions on Package Control

#### Workarounds
1. Use generic SQL syntax
2. External ClickHouse CLI client
3. Custom syntax definition (advanced users)

#### Recommendation
For ClickHouse-specific work, consider VSCode or JetBrains tools. Sublime Text suitable for casual SQL editing with external client.

---

## Language Server Protocol (LSP)

**Status:** No ClickHouse-specific LSP exists (as of 2025-11)

### Generic SQL Language Servers

#### 1. sqls
**Repository:** https://github.com/sqls-server/sqls  
**Language:** Go  
**Status:** Appears unmaintained

**Features:**
- Generic SQL LSP implementation
- Auto-completion
- Hover documentation
- Basic error checking

**Limitations:**
- No ClickHouse-specific syntax support
- May not recognize ClickHouse extensions (arrays, nested columns, table engines)

---

#### 2. sql-language-server
**Repository:** https://github.com/joe-re/sql-language-server  
**Configuration:** Requires `.sqllsrc.json`

**Features:**
- Generic SQL language features
- Must restart after config changes

**Limitations:**
- Generic SQL only
- Limited ClickHouse support

---

### ClickHouse-Specific LSP Request

**GitHub Issue:** ClickHouse/ClickHouse#56637  
**Date:** November 2023  
**Status:** Open feature request

**Requested Features:**
- Auto-complete for ClickHouse functions/syntax
- Error checking for ClickHouse SQL
- Hover documentation for ClickHouse-specific features
- Go-to-definition for ClickHouse objects

**Challenge:**
ClickHouse uses extended SQL with:
- Arrays and nested data structures
- ClickHouse-specific functions (approximate, URI functions)
- Custom table engines
- Materialized views and projections

Generic SQL LSPs don't support these features.

---

## Standalone GUI Clients (Comparison)

While not IDE integrations, these tools are worth mentioning for completeness:

### DBeaver (Free/Open Source)

**Website:** https://dbeaver.io  
**License:** Open source (Community) / Commercial (Ultimate)

#### Features
- Universal database tool (supports 80+ databases)
- JDBC/ODBC connectivity
- SQL editor with syntax highlighting
- Schema browser
- Data editor
- ER diagrams (Ultimate)
- Result-set pivoting (Ultimate)
- AI chat (Ultimate)

#### ClickHouse Support
- Native ClickHouse driver
- Clusters, partitions, materialized views

#### Pros
- Free tier includes ClickHouse
- Cross-platform
- Comprehensive features
- Multi-database support

#### Cons
- Java-based (high RAM usage)
- UI can lag on wide result sets
- Overwhelming for beginners
- Not an IDE integration (standalone app)

---

### TablePlus (Commercial)

**Website:** https://tableplus.com  
**License:** Free trial / Paid license  
**ClickHouse Support:** Added early 2025

#### Features
- Multi-database GUI
- SQL query editor with real-time feedback
- Simple, clean interface
- Native application (fast)

#### Pros
- Blazing fast performance
- Lightweight
- Intuitive UI
- Affordable pricing

#### Cons
- No built-in AI tools
- No team workspaces
- Less feature-rich than DBeaver Ultimate

---

### Beekeeper Studio

**Website:** https://www.beekeeperstudio.io  
**License:** Open source / Commercial (Ultimate)

#### Features
- Modern SQL editor
- Cross-platform
- ClickHouse support

---

### Tabix

**Type:** Web-based ClickHouse client  
**Use Case:** Browser-based querying

---

## Recommended Setup for Python-Centric Development

Based on research findings, here's the optimal ClickHouse IDE setup for Python data engineering workflows:

### Primary Environment: VSCode

**Extensions to Install:**
```bash
# Core database extension
code --install-extension ultram4rine.sqltools-clickhouse-driver

# Optional: Database Client
code --install-extension cweijan.vscode-database-client2
```

**Configuration Example (SQLTools):**

Create `.vscode/settings.json`:
```json
{
  "sqltools.connections": [
    {
      "name": "ClickHouse Local",
      "driver": "ClickHouse",
      "server": "localhost",
      "port": 8123,
      "username": "default",
      "password": "",
      "database": "default"
    },
    {
      "name": "ClickHouse Cloud",
      "driver": "ClickHouse",
      "server": "your-host.clickhouse.cloud",
      "port": 8443,
      "username": "default",
      "password": "your-password",
      "database": "default",
      "connectionString": "https://your-host.clickhouse.cloud:8443?ssl=true"
    }
  ]
}
```

---

### Jupyter Integration

**Install Packages:**
```bash
pip install jupysql clickhouse-sqlalchemy clickhouse-connect
```

**Notebook Setup:**
```python
# Option 1: JupySQL (SQL-first workflow)
%load_ext sql
%config SqlMagic.autocommit=False
%sql clickhouse://default:@localhost:8123/default

# Option 2: clickhouse-connect (Python-first workflow)
import clickhouse_connect
client = clickhouse_connect.get_client(host='localhost', port=8123)
df = client.query_df("SELECT * FROM my_table")
```

---

### Optional: JetBrains Tools

**For Database-Heavy Work:**
- **DataGrip:** Standalone database IDE (best ClickHouse integration)
- **PyCharm Pro:** Python IDE + embedded DataGrip

**Connection Setup:**
1. Data Sources → New → ClickHouse
2. Port: 8123 (local) or 8443 (cloud)
3. For cloud: Add `?ssl=true` to JDBC URL

---

### Workflow Recommendations

**Scenario 1: Exploratory Data Analysis**
- **Tool:** Jupyter notebook with clickhouse-connect
- **Workflow:** Query → DataFrame → pandas/visualization

**Scenario 2: SQL Development**
- **Tool:** VSCode with SQLTools ClickHouse Driver
- **Workflow:** Write SQL → Execute → Refine

**Scenario 3: Production ETL Pipeline**
- **Tool:** VSCode for Python code + clickhouse-connect library
- **Workflow:** Python scripts with embedded SQL

**Scenario 4: Database Design/Migration**
- **Tool:** DataGrip or PyCharm Pro
- **Workflow:** Schema design → DDL → data migration → validation

---

## Configuration Examples

### VSCode SQLTools Connection

**Workspace Settings (`.vscode/settings.json`):**
```json
{
  "sqltools.connections": [
    {
      "name": "ClickHouse Dev",
      "driver": "ClickHouse",
      "server": "localhost",
      "port": 8123,
      "username": "default",
      "password": "",
      "database": "default"
    }
  ],
  "sqltools.useNodeRuntime": true,
  "sqltools.autoOpenSessionFiles": false
}
```

**Usage:**
1. Open Command Palette (Cmd+Shift+P)
2. "SQLTools: Connect" → Select connection
3. Write SQL in `.sql` file
4. Execute with Run icon or keyboard shortcut

---

### Jupyter Notebook Connection Snippet

**JupySQL Approach:**
```python
# Cell 1: Setup
%pip install --quiet jupysql clickhouse-sqlalchemy
%load_ext sql
%config SqlMagic.autocommit=False

# Cell 2: Connect
%sql clickhouse://default:@localhost:8123/default

# Cell 3: Query
%%sql
SELECT 
    toStartOfMonth(event_time) as month,
    count() as events
FROM events
WHERE event_time >= today() - INTERVAL 1 YEAR
GROUP BY month
ORDER BY month
```

**clickhouse-connect Approach:**
```python
# Cell 1: Setup
import clickhouse_connect
import pandas as pd

# Cell 2: Connect
client = clickhouse_connect.get_client(
    host='localhost',
    port=8123,
    username='default',
    password=''
)

# Cell 3: Query to DataFrame
query = """
SELECT 
    toStartOfMonth(event_time) as month,
    count() as events
FROM events
WHERE event_time >= today() - INTERVAL 1 YEAR
GROUP BY month
ORDER BY month
"""
df = client.query_df(query)

# Cell 4: Visualize
df.plot(x='month', y='events', kind='bar')
```

---

### DataGrip/PyCharm Connection

**JDBC URL (Local):**
```
jdbc:clickhouse://localhost:8123/default
```

**JDBC URL (Cloud with SSL):**
```
jdbc:clickhouse://your-host.clickhouse.cloud:8443/default?ssl=true
```

**Settings:**
- **Host:** localhost (or cloud hostname)
- **Port:** 8123 (HTTP) or 8443 (HTTPS)
- **User:** default
- **Password:** (your password)
- **Database:** default
- **Driver:** ClickHouse (latest stable)

---

### Python clickhouse-connect Configuration

**Connection Class:**
```python
import clickhouse_connect
from typing import Optional

class ClickHouseClient:
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 8123,
        username: str = 'default',
        password: str = '',
        database: str = 'default',
        secure: bool = False
    ):
        self.client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            secure=secure
        )
    
    def query_df(self, query: str):
        """Execute query and return pandas DataFrame"""
        return self.client.query_df(query)
    
    def insert_df(self, table: str, df):
        """Insert pandas DataFrame into table"""
        self.client.insert_df(table, df)
    
    def execute(self, query: str):
        """Execute query without return"""
        self.client.command(query)

# Usage
ch = ClickHouseClient(host='localhost')
df = ch.query_df("SELECT * FROM my_table LIMIT 10")
```

---

## Summary Matrix

| Tool | Type | ClickHouse Support | Best For | Cost | Rating |
|------|------|-------------------|----------|------|--------|
| **DataGrip** | Standalone IDE | Native | Database design, complex queries | Paid | ⭐⭐⭐⭐⭐ |
| **PyCharm Pro** | Python IDE | Embedded DataGrip | Python + database workflows | Paid | ⭐⭐⭐⭐⭐ |
| **VSCode SQLTools** | Editor Extension | Driver | SQL development, lightweight | Free | ⭐⭐⭐⭐ |
| **VSCode Database Client** | Editor Extension | Via extension pack | Multi-DB management | Free | ⭐⭐⭐ |
| **DBCode** | Editor Extension | Native | Feature-rich, AI tools | Paid | ⭐⭐⭐⭐ |
| **JupySQL** | Jupyter Extension | Via SQLAlchemy | Notebooks, data analysis | Free | ⭐⭐⭐⭐ |
| **clickhouse-connect** | Python Library | Official | Production pipelines | Free | ⭐⭐⭐⭐⭐ |
| **Emacs sql-clickhouse** | Editor Plugin | Basic | Emacs users only | Free | ⭐⭐ (archived) |
| **Vim** | Editor | None | N/A (use CLI) | Free | ⭐ |
| **Sublime Text** | Editor | None | N/A (use CLI) | Free | ⭐ |

**Legend:**
- ⭐⭐⭐⭐⭐ Excellent ClickHouse support
- ⭐⭐⭐⭐ Good support with minor limitations
- ⭐⭐⭐ Basic support, usable
- ⭐⭐ Limited/outdated
- ⭐ No specific support

---

## Key Findings

1. **JetBrains Dominance:** DataGrip and PyCharm offer the most comprehensive ClickHouse IDE integration with native dialect support.

2. **VSCode Ecosystem:** Multiple extension options, with SQLTools ClickHouse Driver being most popular and actively maintained.

3. **Jupyter Production-Ready:** JupySQL and clickhouse-connect provide solid notebook integration for data science workflows.

4. **Traditional Editors:** Vim and Sublime Text lack ClickHouse-specific plugins. Emacs has archived plugin. Use ClickHouse CLI for these editors.

5. **No ClickHouse LSP:** Generic SQL language servers exist but don't support ClickHouse-specific syntax extensions.

6. **Python-First Recommended:** For Python developers, use VSCode + clickhouse-connect for best developer experience.

---

## Research Limitations

- Extension marketplace data represents snapshot at research date (2025-11-17)
- Version numbers and feature sets may change
- Some extensions have limited review data
- Cloud-specific features not exhaustively tested
- Focused on macOS/Linux environments per project requirements

---

## References

- ClickHouse Official Docs: https://clickhouse.com/docs/integrations
- VSCode Marketplace: https://marketplace.visualstudio.com
- JetBrains Documentation: https://www.jetbrains.com/help
- GitHub Repositories: Various (linked throughout report)

---

**Report Prepared By:** IDE Integrations Research Agent  
**Date:** 2025-11-17  
**Project:** gapless-crypto-data ClickHouse migration research
