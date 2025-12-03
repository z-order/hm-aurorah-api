"""
Task endpoints
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.task import Task, TaskCreate, TaskRead, TaskUpdate

router = APIRouter()


@router.get("/", response_model=list[TaskRead])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all tasks
    """
    result = await db.execute(select(Task).offset(skip).limit(limit))
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get task by ID
    """
    result = await db.execute(select(Task).where(Task.id == task_id))  # type: ignore[arg-type]
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.get("/project/{project_id}", response_model=list[TaskRead])
async def get_project_tasks(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all tasks for a specific project
    """
    result = await db.execute(
        select(Task).where(Task.project_id == project_id).offset(skip).limit(limit)  # type: ignore[arg-type]
    )
    tasks = result.scalars().all()
    return tasks


@router.get("/user/{user_id}", response_model=list[TaskRead])
async def get_user_tasks(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all tasks assigned to a specific user
    """
    result = await db.execute(
        select(Task).where(Task.assigned_to == user_id).offset(skip).limit(limit)  # type: ignore[arg-type]
    )
    tasks = result.scalars().all()
    return tasks


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create new task
    """
    task = Task(**task_data.model_dump())

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return task


@router.put("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update task
    """
    result = await db.execute(select(Task).where(Task.id == task_id))  # type: ignore[arg-type]
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Update task fields
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_at = datetime.now(UTC)

    db.add(task)
    await db.commit()
    await db.refresh(task)

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete task
    """
    result = await db.execute(select(Task).where(Task.id == task_id))  # type: ignore[arg-type]
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    await db.delete(task)
    await db.commit()

    return None
