"""
Download queue manager with threading support.
"""
import threading
import uuid
from queue import Queue
from typing import Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import config
from .downloader import Downloader, DownloadProgress, DownloadResult, DownloadStatus


@dataclass
class DownloadTask:
    id: str
    url: str
    title: str = ""
    format_id: Optional[str] = None
    cookie_file: Optional[str] = None
    audio_only: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    result: Optional[DownloadResult] = None
    downloader: Optional[Downloader] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "status": self.progress.status.value,
            "progress": self.progress.progress,
            "speed": self.progress.speed,
            "eta": self.progress.eta,
            "filename": self.progress.filename,
            "error": self.progress.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class DownloadManager:
    """Manages download queue with concurrent execution."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._tasks: Dict[str, DownloadTask] = {}
        self._executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_DOWNLOADS)
        self._progress_callbacks: list[Callable[[str, DownloadProgress], None]] = []
        self._initialized = True

    def add_progress_callback(self, callback: Callable[[str, DownloadProgress], None]):
        """Add a callback for progress updates."""
        self._progress_callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[str, DownloadProgress], None]):
        """Remove a progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def _notify_progress(self, task_id: str, progress: DownloadProgress):
        """Notify all callbacks of progress update."""
        for callback in self._progress_callbacks:
            try:
                callback(task_id, progress)
            except Exception:
                pass

    def add_download(
        self,
        url: str,
        title: str = "",
        format_id: Optional[str] = None,
        cookie_file: Optional[str] = None,
        audio_only: bool = False,
    ) -> str:
        """Add a new download to the queue and start it."""
        task_id = str(uuid.uuid4())[:8]

        task = DownloadTask(
            id=task_id,
            url=url,
            title=title,
            format_id=format_id,
            cookie_file=cookie_file,
            audio_only=audio_only,
        )

        self._tasks[task_id] = task
        self._executor.submit(self._execute_download, task_id)

        return task_id

    def _execute_download(self, task_id: str):
        """Execute a download task."""
        import logging
        logger = logging.getLogger('video_downloader.download_manager')

        task = self._tasks.get(task_id)
        if not task:
            return

        try:
            task.started_at = datetime.now()

            downloader = Downloader(
                url=task.url,
                format_id=task.format_id,
                cookie_file=task.cookie_file,
                audio_only=task.audio_only,
            )
            task.downloader = downloader

            def progress_callback(progress: DownloadProgress):
                task.progress = progress
                if not task.title and progress.filename:
                    task.title = progress.filename
                self._notify_progress(task_id, progress)

            downloader.set_progress_callback(progress_callback)

            # Get video info first for title
            try:
                info = downloader.get_info()
                task.title = info.get("title", task.url)
            except Exception:
                pass

            result = downloader.download()
            task.result = result
            task.completed_at = datetime.now()

            if result.success and result.title:
                task.title = result.title
        except Exception as e:
            logger.error(f"Uncaught exception in download task {task_id}: {e}", exc_info=True)
            task.progress.status = DownloadStatus.ERROR
            task.progress.error = str(e)
            task.completed_at = datetime.now()
            self._notify_progress(task_id, task.progress)

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[DownloadTask]:
        """Get all tasks."""
        return list(self._tasks.values())

    def get_queue(self) -> list[dict]:
        """Get all tasks as dictionaries."""
        return [task.to_dict() for task in self._tasks.values()]

    def cancel_download(self, task_id: str) -> bool:
        """Cancel a download by ID."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.downloader:
            task.downloader.cancel()
            return True

        if task.progress.status == DownloadStatus.PENDING:
            task.progress.status = DownloadStatus.CANCELLED
            return True

        return False

    def remove_task(self, task_id: str) -> bool:
        """Remove a completed/cancelled task."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.progress.status in (
            DownloadStatus.COMPLETED,
            DownloadStatus.ERROR,
            DownloadStatus.CANCELLED,
        ):
            del self._tasks[task_id]
            return True

        return False

    def clear_completed(self):
        """Remove all completed, errored, or cancelled tasks."""
        to_remove = [
            task_id
            for task_id, task in self._tasks.items()
            if task.progress.status in (
                DownloadStatus.COMPLETED,
                DownloadStatus.ERROR,
                DownloadStatus.CANCELLED,
            )
        ]
        for task_id in to_remove:
            del self._tasks[task_id]

    def shutdown(self):
        """Shutdown the download manager."""
        for task in self._tasks.values():
            if task.downloader and task.progress.status == DownloadStatus.DOWNLOADING:
                task.downloader.cancel()
        self._executor.shutdown(wait=False)
