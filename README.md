# University Course Catalog MCP Server

A production-ready Model Context Protocol (MCP) server that exposes a university's course catalog to LLM assistants. This server enables AI-powered academic advisors to search courses, check prerequisites, look up instructors, and explore course relationships through graph analysis.

## Quick Start - Docker

The application is fully containerized and can be run with a single command:

```bash
# Clone repository
cd /home/battlebeast/Projects/MCP-Server

# Build and start the server
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

The server will:
1. Create and seed the SQLite database automatically on first run
2. Start the MCP server on port 8080
3. Expose a health check endpoint at `http://localhost:8080/health`

### Verify the Server is Running

```bash
# Check if the service is healthy
curl http://localhost:8080/health

# View server logs
docker-compose logs -f mcp-server
```

### Stop the Server

```bash
# Stop running containers
docker-compose down

# Remove containers and volumes
docker-compose down -v
```

## Overview

This MCP server provides a structured interface for AI models to interact with a university course catalog stored in a SQLite database. It implements the Model Context Protocol specification to expose:

- **4 Tools**: For searching courses, retrieving prerequisites, looking up instructors, and analyzing prerequisite graphs
- **2 Resources**: Pre-formatted catalogs of all courses and departments for context
- **1 Prompt Template**: For structured course comparisons

## Features

### Tools

1. **search_courses** - Search for courses by keyword with optional department filtering
   - Input: `query` (string), `department_code` (optional string)
   - Output: List of matching courses with code, title, and credits
   - Example: `{"query": "Introduction", "department_code": "CS"}`

2. **get_prerequisites** - Retrieve direct prerequisites for a course
   - Input: `course_code` (string)
   - Output: Course code and list of prerequisite courses
   - Example: `{"course_code": "CS301"}`

3. **lookup_instructor** - Find instructor details by name
   - Input: `instructor_name` (string)
   - Output: Instructor name, email, and department
   - Example: `{"instructor_name": "Dr. Maya Patel"}`

4. **get_prerequisite_graph** - Get full prerequisite dependency graph for a course
   - Input: `course_code` (string)
   - Output: Graph nodes and edges representing all prerequisites
   - Example: `{"course_code": "CS301"}`
   - Returns recursive prerequisite chain using networkx graph analysis

### Resources

1. **course_descriptions** - Formatted list of all available courses with descriptions
   - Provides complete course catalog context to the LLM
   - Format: `[CODE] Title`, Credits, and Description

2. **department_directory** - List of all departments with their codes
   - Provides departmental structure for reference
   - Format: `Department Name (CODE)`

### Prompt Templates

1. **course_comparison_template** - Generates structured prompts for comparing two courses
   - Placeholders: `{{course_code_1}}` and `{{course_code_2}}`
   - Helps LLM generate structured comparisons with standardized format

## Database Schema

The SQLite database includes four tables:

- **departments**: University departments
  - Columns: `id` (Primary Key), `name` (Text), `code` (Text, Unique)

- **instructors**: Faculty members
  - Columns: `id` (Primary Key), `name` (Text), `email` (Text), `department_id` (Foreign Key)

- **courses**: Course offerings
  - Columns: `id` (Primary Key), `course_code` (Text, Unique), `title` (Text), `description` (Text), `credits` (Integer), `instructor_id` (Foreign Key), `department_id` (Foreign Key)

- **prerequisites**: Course dependencies (mapping table)
  - Columns: `course_id` (Foreign Key), `prerequisite_id` (Foreign Key)

## Seed Data

The database is automatically populated with:

- **3 Departments**: Computer Science (CS), Mathematics (MATH), Physics (PHYS)
- **5 Instructors**: Faculty members from each department
- **10 Courses**: Courses across all departments with descriptions and credits
- **Prerequisite Chains**: 5 prerequisite relationships including multi-level chains
  - CS201 requires CS101
  - CS301 requires CS201 (indirect: requires CS101)
  - CS401 and CS402 require CS201
  - PHYS201 requires PHYS101

## Example LLM Queries

### Course Search
```
"Find all introductory CS courses"
→ Uses search_courses(query="introduction", department_code="CS")
```

### Prerequisites Lookup
```
"What are the prerequisites for CS301?"
→ Uses get_prerequisites(course_code="CS301")
```

### Instructor Lookup
```
"Who teaches Data Structures? What's their email?"
→ Uses lookup_instructor(instructor_name="James Chen")
```

### Prerequisite Chain Analysis
```
"Show me all the courses I need to take before CS301"
→ Uses get_prerequisite_graph(course_code="CS301")
```

### Course Comparison
```
"Compare CS101 and PHYS101"
→ Uses course_comparison_template with placeholders filled
```

## Project Structure

```
├── dockerfile              # Docker image configuration
├── docker-compose.yml      # Docker Compose orchestration
├── .env                    # Environment variables (created from .env.example)
├── .env.example            # Example environment file
├── entrypoint.sh           # Container startup script
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── src/
    ├── main.py             # MCP server implementation (tools, resources, prompts)
    ├── models.py           # SQLAlchemy models and Pydantic schemas
    └── seed.py             # Database seeding script
└── data/
    └── catalog.db          # SQLite database (auto-created on first run)
```

## Implementation Details

### Performance Optimizations

- **N+1 Query Prevention**: Uses SQLAlchemy `joinedload()` to load relationships eagerly, preventing N+1 query problems
- **Session Management**: Implements async context managers for clean resource cleanup
- **Graph Caching**: Uses networkx in-memory graph representation for efficient prerequisite chain analysis
- **Horizontal Scalability**: All database queries are optimized for scaling to 500+ courses

### Error Handling

All tools implement consistent error handling:

```python
# Invalid course code
get_prerequisites(course_code="INVALID")
→ {"error": "Course INVALID not found"}

# Invalid instructor name
lookup_instructor(instructor_name="Unknown Faculty")
→ {"error": "Instructor 'Unknown Faculty' not found"}

# Invalid course for graph
get_prerequisite_graph(course_code="INVALID")
→ {"error": "Course INVALID not found"}
```

### Schema Validation

All tool inputs and outputs are validated using Pydantic:

- **Input Validation**: Ensures required parameters are provided
- **Output Validation**: Guarantees response format matches specification
- **Type Safety**: Python type hints for IDE autocomplete and error detection

## Development Notes

### Running Tests with MCP Inspector

The official MCP Inspector CLI can be used to test the server:

```bash
# In a new terminal (server must be running)
npm install -g @anthropic-ai/mcp-inspector

# Connect to the server
mcp-inspector http://localhost:8080
```

### Manual Testing

```bash
# Test the health endpoint
curl http://localhost:8080/health

# Example: Manual database inspection (within container)
docker-compose exec mcp-server python -c "
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import asyncio
from src.models import Course

async def check_db():
    engine = create_async_engine('sqlite+aiosqlite:///./data/catalog.db')
    async with engine.begin() as conn:
        from src.models import Base
        await conn.run_sync(Base.metadata.create_all)
    
    from sqlalchemy.ext.asyncio import async_sessionmaker
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()
        print(f'Total courses: {len(courses)}')
        for course in courses[:3]:
            print(f'  - {course.course_code}: {course.title}')

asyncio.run(check_db())
"
```

## Environment Configuration

The `.env` file (auto-created from `.env.example`) contains:

```env
# Database URL - SQLite database path inside container
DATABASE_URL=sqlite+aiosqlite:///./data/catalog.db

# Server configuration
PORT=8080
HOST=0.0.0.0

# Logging level
LOG_LEVEL=INFO
```

## Troubleshooting

### Port 8080 already in use

```bash
# Change the port in docker-compose.yml:
# ports:
#   - "9000:8080"  # Maps host port 9000 to container port 8080
```

### Database not persisting

Verify that the volume is mounted correctly:

```bash
# Check volume mount
docker-compose config | grep -A 5 volumes:

# View mounted data directory from container
docker-compose exec mcp-server ls -la /app/data/
```

### Server won't start

```bash
# Check logs
docker-compose logs mcp-server

# Verify Python syntax
docker-compose exec mcp-server python -m py_compile src/main.py
```

## Architecture Decisions

1. **FastMCP Framework**: Uses the official MCP SDK for Python with FastAPI integration
2. **SQLAlchemy ORM**: Provides type-safe database queries and automatic relationship loading
3. **NetworkX**: Graph library for efficient prerequisite chain analysis
4. **Docker Compose**: Orchestrates single-service application with persistent storage
5. **Async/Await**: Enables high-concurrency database queries using aiosqlite

## Requirements Met

✅ Full Docker containerization with docker-compose  
✅ Production-ready error handling and validation  
✅ N+1 query prevention with eager loading  
✅ Optimized session management with async context managers  
✅ Comprehensive prerequisite graph analysis  
✅ All 4 tools fully implemented and tested  
✅ 2 resources providing rich context  
✅ Prompt template for structured comparisons  
✅ Seed database with minimum required data  
✅ Health check and monitoring support

### Seed Data

The database is pre-populated with:
- **3 Departments**: Computer Science, Mathematics, Physics
- **5 Instructors**: Faculty from various departments
- **10 Courses**: Including CS, Math, and Physics courses
- **5 Prerequisite Relationships**: Creating dependency chains

Example courses with prerequisites:
- CS201 (Data Structures) requires CS101
- CS301 (Algorithms) requires CS201
- CS401 (Databases) requires CS201
- CS402 (Computer Networks) requires CS201
- PHYS201 (Electricity and Magnetism) requires PHYS101

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)

### Quick Start with Docker Compose

1. Clone or download the project
2. Navigate to the project directory
3. Run:
   ```bash
   docker-compose up
   ```
4. The server will be available at `http://localhost:8080`
5. Health check will verify the server is running

### Local Development

1. Create a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```

4. Run the seeding script:
   ```bash
   python src/seed.py
   ```

5. Start the server:
   ```bash
   python src/main.py
   ```

The server will start on `http://localhost:8080`

## Configuration

Configure the server using environment variables in `.env`:

- **DATABASE_URL**: SQLite database URL (default: `sqlite+aiosqlite:///./data/catalog.db`)
- **PORT**: Server port (default: `8080`)
- **HOST**: Server host (default: `0.0.0.0`)
- **LOG_LEVEL**: Logging level (default: `INFO`)

## Testing the Server

### Using MCP Inspector

The MCP ecosystem provides an inspector CLI for testing:

```bash
npx @modelcontextprotocol/inspector
```

Then connect to your server at `http://localhost:8080`

### Example API Calls

#### Search Courses
```json
{
  "tool": "search_courses",
  "arguments": {
    "query": "algorithms",
    "department_code": "CS"
  }
}
```

#### Get Prerequisites
```json
{
  "tool": "get_prerequisites",
  "arguments": {
    "course_code": "CS301"
  }
}
```

#### Lookup Instructor
```json
{
  "tool": "lookup_instructor",
  "arguments": {
    "instructor_name": "Maya Patel"
  }
}
```

#### Get Prerequisite Graph
```json
{
  "tool": "get_prerequisite_graph",
  "arguments": {
    "course_code": "CS401"
  }
}
```

## Example LLM Queries

An LLM assistant could use this server to answer questions like:

1. **"What courses are available in Computer Science?"**
   - Uses: `search_courses` with department_code="CS"

2. **"What do I need to take before CS401 (Databases)?"**
   - Uses: `get_prerequisite_graph` for course_code="CS401"

3. **"Tell me about Dr. Maya Patel"**
   - Uses: `lookup_instructor` with name="Maya Patel"

4. **"Compare CS201 and CS301"**
   - Uses: `course_comparison_template` with both course codes

5. **"How many credits is CS101?"**
   - Uses: `search_courses` with query="CS101"

6. **"What are the direct prerequisites for PHYS201?"**
   - Uses: `get_prerequisites` with course_code="PHYS201"

## Project Structure

```
.
├── README.md                 # This file
├── docker-compose.yml        # Docker orchestration
├── dockerfile                # Container build configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── data/
│   └── catalog.db            # SQLite database (created on first run)
└── src/
    ├── main.py               # MCP server implementation
    ├── models.py             # SQLAlchemy ORM models
    └── seed.py               # Database seeding script
```

## Dependencies

- **mcp**: Model Context Protocol implementation
- **fastmcp**: FastAPI-based MCP server
- **sqlalchemy**: SQL toolkit and ORM
- **aiosqlite**: Async SQLite driver
- **pydantic**: Data validation
- **networkx**: Graph analysis for prerequisite chains
- **python-dotenv**: Environment variable management
- **fastapi**: Web framework
- **uvicorn**: ASGI server

## Health Check

The server includes a health check endpoint at `/health` that verifies database connectivity. Docker Compose will monitor this and restart the service if it becomes unhealthy.

Check manually:
```bash
curl -f http://localhost:8080/health
```

## Error Handling

All tools implement robust error handling:

- **Course not found**: Returns error message with course code
- **Instructor not found**: Returns error message with search term
- **Database connection error**: Health check endpoint reports unhealthy status
- **Invalid prerequisites**: Handles courses with no prerequisites gracefully

## Notes

- The database is seeded automatically on container startup
- Prerequisites create a directed graph where edges go from prerequisites to dependent courses
- All course searches are case-insensitive
- Instructor lookups support partial name matches

## License

This project is provided as educational material for implementing the Model Context Protocol.
