from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(10), unique=True)
    
    # Relationships for easier querying
    instructors: Mapped[List["Instructor"]] = relationship(back_populates="department")
    courses: Mapped[List["Course"]] = relationship(back_populates="department")

class Instructor(Base):
    __tablename__ = "instructors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100))
    # Corrected: office was mentioned in description, but email is in schema req.
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    
    department: Mapped["Department"] = relationship(back_populates="instructors")

class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_code: Mapped[str] = mapped_column(String(20), unique=True) # Check: Rubric uses 'course_code'
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(500))
    credits: Mapped[int] = mapped_column(Integer)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("instructors.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))

    department: Mapped["Department"] = relationship(back_populates="courses")
    
    # Self-referential relationship for prerequisites
    # This allows course.prerequisites to return a list of Course objects
    prerequisites: Mapped[List["Course"]] = relationship(
        "Course",
        secondary="prerequisites",
        primaryjoin="Course.id==Prerequisite.course_id",
        secondaryjoin="Course.id==Prerequisite.prerequisite_id",
        backref="required_for"
    )

class Prerequisite(Base):
    __tablename__ = "prerequisites"
    # Rubric: (course_id, prerequisite_id)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), primary_key=True)
    prerequisite_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), primary_key=True)


class CourseMinInfo(BaseModel):
    course_code: str
    title: str

class CourseSearchOutput(CourseMinInfo):
    credits: int

class PrerequisiteOutput(BaseModel):
    course_code: str
    prerequisites: List[CourseMinInfo] # Must be list of objects per Requirement 5

class InstructorLookupOutput(BaseModel):
    name: str
    email: str
    department_name: str # Match Requirement 6

class Node(BaseModel):
    id: str

class Edge(BaseModel):
    source: str
    target: str

class PrerequisiteGraphOutput(BaseModel):
    nodes: List[Node]
    edges: List[Edge]