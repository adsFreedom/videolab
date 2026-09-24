"""Complex Steerable Pyramid через pyrtools."""
import numpy as np


def build_pyramid(
    image: np.ndarray,
    levels: int = 4,
    orientations: int = 4,
) -> dict:
    """
    Строит Complex Steerable Pyramid.

    Args:
        image: 2D массив (grayscale), float32.
        levels: количество уровней.
        orientations: количество ориентаций.

    Returns:
        dict с ключами:
          - 'lowpass': низкочастотный остаток
          - 'bands': dict[(level, orientation)] = complex array
    """
    import pyrtools as pt

    # pyrtools требует float в диапазоне примерно 0..1 или 0..255
    img = image.astype(np.float32)

    # Создаём пирамиду
    pyr = pt.pyramids.SteerablePyramidFreq(
        img,
        height=levels,
        order=orientations - 1,  # pyrtools использует order = orientations - 1
        is_complex=True,
    )

    result = {
        "lowpass": None,
        "bands": {},
    }

    # Собираем коэффициенты
    for key, coeff in pyr.pyr_coeffs.items():
        if isinstance(key, tuple):
            level, orient = key
            result["bands"][(level, orient)] = np.asarray(coeff)
        elif key == "residual_lowpass":
            result["lowpass"] = np.asarray(coeff)
        elif key == "residual_highpass":
            # Игнорируем highpass (он не нужен по задаче)
            pass

    return result


def split_real_imag(complex_coeff: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Разделяет комплексные коэффициенты на real и imag."""
    return np.real(complex_coeff), np.imag(complex_coeff)