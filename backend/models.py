import math
from typing import List
from sqlalchemy import Column, DateTime, Text, String, Integer, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    secret: Mapped[str] = mapped_column(String)
    project_list: Mapped[List["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parent_userid: Mapped[int] = mapped_column(ForeignKey("user_accounts.id"))
    owner: Mapped["User"] = relationship(back_populates="project_list")
    feature_list: Mapped[List["Feature"]] = relationship(back_populates="parent_project", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    @property
    def progress(self) -> int:
        all_tasks = []
        for feature in self.feature_list:
            all_tasks.extend(feature.task_list)
        
        if not all_tasks:
            return 0
        
        completed_points = 0
        total_points = 0

        for task in all_tasks:
            if task.completed:
                completed_points += task.points
            total_points += task.points
        if total_points == 0:
            return 0
        
        return math.ceil((completed_points/total_points) * 100)

class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    parent_project: Mapped["Project"] = relationship(back_populates="feature_list")
    name: Mapped[str] = mapped_column(String(255))

    description: Mapped[str] = mapped_column(Text, nullable=True)
    task_list: Mapped[List["Task"]] = relationship(back_populates="parent_feature", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def progress(self) -> int:
        if not self.task_list:
            return 0

        completed_points = 0
        total_points = 0

        for task in self.task_list:
            if task.completed:
                completed_points += task.points
            total_points += task.points
        if total_points == 0:
            return 0
        return math.ceil((completed_points/total_points) * 100)
    
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature_id: Mapped[int] = mapped_column(ForeignKey('features.id'))
    parent_feature: Mapped["Feature"] = relationship(back_populates="task_list")
    name: Mapped[str] = mapped_column(String(255))

    description: Mapped[str] = mapped_column(Text, nullable=True)
    work_notes: Mapped[List["Note"]] = relationship(back_populates="parent_task", cascade="all, delete-orphan")
    points: Mapped[int] = mapped_column(Integer, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("points >= 1 AND points <= 10"),
    )

    @property
    def progress(self) -> int:
        return 100 if self.completed else 0


class Note(Base):
    __tablename__ = "work_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'))
    parent_task: Mapped["Task"] = relationship(back_populates="work_notes")

    content: Mapped[str] = mapped_column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())