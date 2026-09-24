"""Обработчики VideoLab. Импорт модулей регистрирует обработчики."""
from processors import crop
from processors import extract_frames
from processors import resize  # noqa: F401
from processors.yiq_steerable import YIQSteerableProcessor  # noqa: F401