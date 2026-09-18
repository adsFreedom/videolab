"""Регистрация исходного видео в source_0."""
import shutil
from pathlib import Path

from core.utils import load_yaml, save_yaml, timestamp


def register_source_video(source_node_path: str, video_path: str) -> None:
    """Регистрирует исходное видео в корневом узле source_0."""
    source_node_path = Path(source_node_path)
    video_path = Path(video_path).resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"Видео не найдено: {video_path}")

    target = source_node_path / video_path.name
    if not target.exists():
        shutil.copy2(video_path, target)

    yaml_file = source_node_path / f"{source_node_path.name}.yaml"
    data = load_yaml(yaml_file)
    data["input_file"] = str(target)
    data["last_run_at"] = timestamp()
    save_yaml(yaml_file, data)