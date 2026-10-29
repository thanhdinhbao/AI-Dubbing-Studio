import os
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from app.models import ProjectData, DialogueSegment, MediaInfo
from app.utils.paths import sanitize_filename, get_default_projects_dir
from app.exceptions import ProjectError

logger = logging.getLogger("AIDubbingStudio.ProjectManager")


class ProjectManager:
    """Handles creating, loading, saving, and managing project workspaces."""

    def __init__(self, base_projects_dir: Optional[Path] = None):
        self.base_projects_dir = base_projects_dir or get_default_projects_dir()
        self.current_project: Optional[ProjectData] = None

    def create_project(self, name: str, video_path: str = "") -> ProjectData:
        """Create a new project workspace directory and metadata file."""
        clean_name = sanitize_filename(name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{clean_name}_{timestamp}"
        proj_dir = self.base_projects_dir / folder_name

        try:
            proj_dir.mkdir(parents=True, exist_ok=True)
            (proj_dir / "audio").mkdir(exist_ok=True)
            (proj_dir / "tts").mkdir(exist_ok=True)
            (proj_dir / "output").mkdir(exist_ok=True)
            (proj_dir / "cache").mkdir(exist_ok=True)

            project = ProjectData(
                name=name,
                project_dir=str(proj_dir),
                video_path=video_path
            )
            self.current_project = project
            self.save_project(project)
            logger.info(f"Created project '{name}' at {proj_dir}")
            return project
        except Exception as e:
            raise ProjectError(f"Không thể tạo dự án '{name}': {e}")

    def save_project(self, project: Optional[ProjectData] = None) -> str:
        """Save project state to project.json."""
        proj = project or self.current_project
        if not proj:
            raise ProjectError("Không có dự án hiện tại để lưu.")

        proj.updated_at = datetime.now().isoformat()
        proj_dir = Path(proj.project_dir)
        proj_dir.mkdir(parents=True, exist_ok=True)
        json_path = proj_dir / "project.json"

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(proj.model_dump_json(indent=2))
            logger.info(f"Project saved to {json_path}")
            return str(json_path)
        except Exception as e:
            raise ProjectError(f"Không thể lưu dự án: {e}")

    def load_project(self, project_path: str | Path) -> ProjectData:
        """Load project from project.json or project folder."""
        path = Path(project_path)
        if path.is_dir():
            path = path / "project.json"

        if not path.exists():
            raise ProjectError(f"Không tìm thấy file dự án: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            project = ProjectData.model_validate(raw)
            # Ensure workspace directory points to actual location
            project.project_dir = str(path.parent.resolve())
            self.current_project = project
            logger.info(f"Successfully loaded project '{project.name}' from {path}")
            return project
        except Exception as e:
            raise ProjectError(f"Lỗi khi đọc file dự án {path}: {e}")

    def list_saved_projects(self) -> List[dict]:
        """List all valid projects found in base_projects_dir."""
        results = []
        if not self.base_projects_dir.exists():
            return results

        for child in self.base_projects_dir.iterdir():
            if child.is_dir():
                pj_file = child / "project.json"
                if pj_file.exists():
                    try:
                        with open(pj_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        results.append({
                            "name": data.get("name", child.name),
                            "project_id": data.get("project_id", ""),
                            "project_dir": str(child),
                            "updated_at": data.get("updated_at", ""),
                            "video_path": data.get("video_path", "")
                        })
                    except Exception:
                        continue
        results.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return results

