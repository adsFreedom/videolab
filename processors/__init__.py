"""Обработчики VideoLab. Импорт модулей регистрирует обработчики."""
from processors import crop
from processors import extract_frames
from processors import resize
from processors.yiq_csp import YIQCSPProcessor
from processors.yiq_csp_inverse import YIQCSPInverseProcessor
from processors.motion_magnify import MotionMagnifyProcessor

__all__ = []