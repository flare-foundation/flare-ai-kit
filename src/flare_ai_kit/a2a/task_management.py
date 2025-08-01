"""
TaskManager module.

contains the TaskManager class with methods for handling\
CRUD operations on tasks.
"""

import sqlite3
import uuid
from pathlib import Path
from typing import ClassVar

from flare_ai_kit.a2a.schemas import Task, TaskState, TaskStatus


class TaskManager:
    """class responsible for task CRUD operations (SQLite supported)."""

    terminal_task_state: ClassVar[list[TaskState]] = [
        TaskState.canceled,
        TaskState.completed,
        TaskState.failed,
        TaskState.rejected,
        TaskState.unknown,
    ]

    def __init__(self, db_path: Path = Path("flare_a2a.db")) -> None:
        """Init method for the task manager."""
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self._create_task_table()
        self.tasks: dict[str, Task] = {}
        self.cancelled_tasks: set[str] = set()

    def _create_task_table(self) -> None:
        """Create the tasks table if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remote_task_id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.cursor.execute(query)
        self.connection.commit()

    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        return uuid.uuid4().hex

    def add_task(self, remote_task_id: str, status: str) -> None:
        """Insert a new task into the database with remote task ID."""
        query = """
        INSERT INTO tasks (remote_task_id, status) VALUES (?, ?);
        """
        self.cursor.execute(query, (remote_task_id, status))
        self.connection.commit()

    def update_task(self, remote_task_id: str, status: str) -> None:
        """Update the task status and result."""
        query = """
        UPDATE tasks
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE remote_task_id = ?;
        """
        self.cursor.execute(query, (status, remote_task_id))
        self.connection.commit()

    def upsert_task(self, remote_task_id: str, status: str) -> None:
        """Insert a new task or update existing task's status."""
        query = """
        INSERT INTO tasks (remote_task_id, status, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(remote_task_id) DO UPDATE SET
            status = excluded.status,
            updated_at = CURRENT_TIMESTAMP;
        """
        self.cursor.execute(query, (remote_task_id, status))
        self.connection.commit()

    def create_task(self, task_id: str) -> Task:
        """Create a task and save it into the database."""
        task = Task(
            id=task_id,
            status=TaskStatus(state=TaskState.submitted),
        )
        self.tasks[task_id] = task
        self.add_task(task_id, TaskState.submitted)
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Retrieve task by ID."""
        task = self.tasks.get(task_id)
        if task is None:
            # Fetch from DB if not in memory
            query = "SELECT * FROM tasks WHERE remote_task_id = ?"
            self.cursor.execute(query, (task_id,))
            row = self.cursor.fetchone()
            if row:
                task = Task(id=row[0], status=TaskStatus(state=row[2]))
                self.tasks[task_id] = task
        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """Update task status in both memory and database."""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.update_task(task_id, status.state)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task and update status in both memory and database."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status.state in self.terminal_task_state:
                return False
            task.status = TaskStatus(state=TaskState.canceled)
            self.cancelled_tasks.add(task_id)
            self.update_task(task_id, TaskState.canceled)
            return True
        return False

    def is_cancelled(self, task_id: str) -> bool:
        """Check if the task is cancelled."""
        return task_id in self.cancelled_tasks
