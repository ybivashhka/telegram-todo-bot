import sqlite3
from datetime import datetime, timedelta
import logging
import csv
import os
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'tasks.db')

class Task:
    def __init__(self, id: int, user_id: int, text: str, category: str, deadline: Optional[str], completed: int, created_at: str):
        self.id = id
        self.user_id = user_id
        self.text = text
        self.category = category
        self.deadline = deadline
        self.completed = completed
        self.created_at = created_at

class Category:
    def __init__(self, user_id: int, name: str):
        self.user_id = user_id
        self.name = name

class TaskManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def init_db(self):
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS tasks
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              user_id INTEGER,
                              task TEXT,
                              category TEXT,
                              deadline TEXT,
                              completed INTEGER,
                              created_at TEXT)''')
                c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON tasks (user_id)')
                c.execute('''CREATE TABLE IF NOT EXISTS categories
                             (user_id INTEGER, category_name TEXT, UNIQUE(user_id, category_name))''')
                c.execute('''CREATE TABLE IF NOT EXISTS subtasks
                             (id INTEGER PRIMARY KEY AUTOINCREMENT,
                              task_id INTEGER,
                              text TEXT,
                              completed INTEGER DEFAULT 0,
                              FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE)''')
                conn.commit()
                logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def add_task(self, user_id: int, text: str, category: str, deadline: Optional[str] = None) -> bool:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('INSERT INTO tasks (user_id, task, category, deadline, completed, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                          (user_id, text, category, deadline if deadline is not None else '', 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                logger.info(f"Task '{text}' added for user {user_id} in category '{category}'.")
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error while adding task: {e}")
            return False

    def add_category(self, user_id: int, category: str) -> bool:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('INSERT OR IGNORE INTO categories (user_id, category_name) VALUES (?, ?)', (user_id, category))
                conn.commit()
                logger.info(f"Category '{category}' added for user {user_id}.")
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error while adding category: {e}")
            return False

    def get_categories(self, user_id: int) -> List[str]:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('SELECT category_name FROM categories WHERE user_id = ?', (user_id,))
                categories = [row[0] for row in c.fetchall()]
                logger.info(f"Retrieved {len(categories)} categories for user {user_id}.")
                return categories
        except sqlite3.Error as e:
            logger.error(f"SQLite error while getting categories: {e}")
            return []

    def get_tasks(self, user_id: Optional[int] = None, completed: int = 0, category: Optional[str] = None) -> List[Task]:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                query = 'SELECT id, user_id, task, category, deadline, completed, created_at FROM tasks WHERE completed = ?'
                params = [completed]
                if user_id is not None:
                    query += ' AND user_id = ?'
                    params.append(user_id)
                if category is not None:
                    query += ' AND category = ?'
                    params.append(category)
                c.execute(query, params)
                rows = c.fetchall()
                logger.info(f"Retrieved {len(rows)} tasks for user {user_id}.")
                return [Task(*row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"SQLite error while getting tasks: {e}")
            return []

    def get_all_incomplete_tasks(self) -> List[Task]:
        return self.get_tasks(completed=0)

    def complete_task(self, task_id: int) -> bool:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('UPDATE tasks SET completed = 1 WHERE id = ?', (task_id,))
                conn.commit()
                logger.info(f"Task {task_id} marked as completed.")
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error while completing task: {e}")
            return False

    def delete_task(self, task_id: int) -> bool:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()
                logger.info(f"Task {task_id} deleted.")
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error while deleting task: {e}")
            return False

    def edit_task(self, task_id: int, text: Optional[str] = None, category: Optional[str] = None, deadline: Optional[str] = None) -> bool:
        try:
            updates = []
            params = []
            if text is not None:
                updates.append('task = ?')
                params.append(text)
            if category is not None:
                updates.append('category = ?')
                params.append(category)
            if deadline is not None:
                updates.append('deadline = ?')
                params.append(deadline)
            if not updates:
                logger.warning(f"No fields to update for task {task_id}.")
                return False
            params.append(task_id)
            query = f'UPDATE tasks SET {", ".join(updates)} WHERE id = ?'
            with self.connect() as conn:
                c = conn.cursor()
                c.execute(query, params)
                conn.commit()
                logger.info(f"Task {task_id} updated.")
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error while editing task {task_id}: {e}")
            return False

    def get_stats(self, user_id: int, days: int) -> List[Tuple[str, int, int]]:
        try:
            date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('SELECT category, completed, COUNT(*) FROM tasks WHERE user_id = ? AND created_at >= ? GROUP BY category, completed',
                          (user_id, date_limit))
                stats = c.fetchall()
                logger.info(f"Stats for user {user_id} for last {days} days: {stats}")
                return stats
        except sqlite3.Error as e:
            logger.error(f"SQLite error while getting stats: {e}")
            return []

    def export_to_csv(self, user_id: int) -> Optional[str]:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('SELECT id, task, category, deadline, completed, created_at FROM tasks WHERE user_id = ?', (user_id,))
                rows = c.fetchall()
                if not rows:
                    logger.warning(f"No tasks to export for user {user_id}")
                    return None
                filename = f'tasks_{user_id}.csv'
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['ID', 'Task', 'Category', 'Deadline', 'Completed', 'Created At'])
                    writer.writerows(rows)
                logger.info(f"Exported tasks for user {user_id} to {filename}")
                return filename
        except Exception as e:
            logger.error(f"Failed to export tasks for user {user_id}: {e}")
            return None

    def add_subtask(self, task_id: int, text: str) -> bool:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('INSERT INTO subtasks (task_id, text, completed) VALUES (?, ?, ?)', (task_id, text, 0))
                conn.commit()
                logger.info(f"Subtask '{text}' added to task {task_id}.")
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error while adding subtask: {e}")
            return False

    def get_subtasks(self, task_id: int) -> List[Tuple[int, str, int]]:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('SELECT id, text, completed FROM subtasks WHERE task_id = ?', (task_id,))
                return c.fetchall()
        except sqlite3.Error as e:
            logger.error(f"SQLite error while getting subtasks: {e}")
            return []

    def complete_subtask(self, subtask_id: int, completed: int = 1) -> bool:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('UPDATE subtasks SET completed = ? WHERE id = ?', (completed, subtask_id))
                conn.commit()
                logger.info(f"Subtask {subtask_id} marked as {'completed' if completed else 'not completed'}.")
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error while completing subtask: {e}")
            return False

    def delete_subtask(self, subtask_id: int) -> bool:
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute('DELETE FROM subtasks WHERE id = ?', (subtask_id,))
                conn.commit()
                logger.info(f"Subtask {subtask_id} deleted.")
                return True
        except sqlite3.Error as e:
            logger.error(f"SQLite error while deleting subtask: {e}")
            return False