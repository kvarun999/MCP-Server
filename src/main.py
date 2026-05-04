import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload
from dotenv import load_dotenv
import networkx as nx

from fastmcp import FastMCP
from src.models import (
    Base, Department, Instructor, Course, Prerequisite,
    CourseSearchOutput, PrerequisiteOutput, CourseMinInfo,
    InstructorLookupOutput, PrerequisiteGraphOutput, Node, Edge
)

load_dotenv()

# Database Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/catalog.db")
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def get_session():
    """Context manager for async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

# Initialize MCP Server
mcp = FastMCP("University Course Catalog")

# --- Tools ---
@mcp.tool()
async def search_courses(query: str, department_code: Optional[str] = None) -> List[CourseSearchOutput]:
    """Searches courses by keyword and optional department."""
    async with get_session() as session:
        stmt = select(Course).where(
            or_(
                Course.title.ilike(f"%{query}%"),
                Course.description.ilike(f"%{query}%"),
                Course.course_code.ilike(f"%{query}%")
            )
        )
        if department_code:
            stmt = stmt.join(Department).where(Department.code == department_code)
        result = await session.execute(stmt)
        courses = result.scalars().all()
        return [CourseSearchOutput(course_code=c.course_code, title=c.title, credits=c.credits) for c in courses]

@mcp.tool()
async def get_prerequisites(course_code: str) -> PrerequisiteOutput:
    """Retrieves direct prerequisites for a course code."""
    async with get_session() as session:
        stmt = select(Course).where(Course.course_code == course_code).options(joinedload(Course.prerequisites))
        result = await session.execute(stmt)
        course = result.scalars().unique().first()
        if not course:
            return PrerequisiteOutput(course_code=course_code, prerequisites=[])
        return PrerequisiteOutput(
            course_code=course_code,
            prerequisites=[CourseMinInfo(course_code=p.course_code, title=p.title) for p in course.prerequisites]
        )

@mcp.tool()
async def lookup_instructor(instructor_name: str) -> InstructorLookupOutput:
    """Finds instructor details by name."""
    async with get_session() as session:
        stmt = select(Instructor).where(Instructor.name.ilike(f"%{instructor_name}%")).options(joinedload(Instructor.department))
        result = await session.execute(stmt)
        instructor = result.scalars().unique().first()
        if not instructor:
            raise ValueError(f"Instructor '{instructor_name}' not found")
        return InstructorLookupOutput(
            name=instructor.name,
            email=instructor.email,
            department_name=instructor.department.name if instructor.department else "Unknown"
        )

@mcp.tool()
async def get_prerequisite_graph(course_code: str) -> PrerequisiteGraphOutput:
    """Returns the full recursive dependency graph for a course."""
    async with get_session() as session:
        stmt = select(Course).options(joinedload(Course.prerequisites))
        result = await session.execute(stmt)
        all_courses = result.scalars().unique().all()
        G = nx.DiGraph()
        for course in all_courses:
            G.add_node(course.course_code)
            for prereq in course.prerequisites:
                G.add_edge(prereq.course_code, course.course_code)
        if course_code not in G:
            raise ValueError(f"Course {course_code} not found")
        relevant_nodes = nx.ancestors(G, course_code) | {course_code}
        subgraph = G.subgraph(relevant_nodes)
        return PrerequisiteGraphOutput(
            nodes=[Node(id=n) for n in subgraph.nodes()],
            edges=[Edge(source=s, target=t) for s, t in subgraph.edges()]
        )

# --- Resources ---
@mcp.resource("catalog://course_descriptions")
async def get_course_descriptions() -> str:
    """List of all courses and descriptions."""
    async with get_session() as session:
        stmt = select(Course).order_by(Course.course_code)
        result = await session.execute(stmt)
        courses = result.scalars().all()
        return "\n".join([f"[{c.course_code}] {c.title}: {c.description}" for c in courses])

@mcp.resource("catalog://department_directory")
async def get_department_directory() -> str:
    """List of all departments and codes."""
    async with get_session() as session:
        stmt = select(Department).order_by(Department.code)
        result = await session.execute(stmt)
        depts = result.scalars().all()
        return "\n".join([f"{d.name} ({d.code})" for d in depts])

# --- Prompts ---
@mcp.prompt("course_comparison_template")
def course_comparison_template(course_code_1: str, course_code_2: str) -> str:
    """Template for comparing two courses."""
    return f"Compare the following two courses: {course_code_1} and {course_code_2}. Use columns for Title, Credits, and Prerequisites."

if __name__ == "__main__":
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    asyncio.run(create_tables())
    
    # Runs natively on PORT 8080 (read from your .env automatically)
    mcp.run(transport="sse")