"""Complex Steerable Pyramid через pyrtools."""
import numpy as np


def build_pyramid(
    image: np.ndarray,
    levels: int = 4,
    orientations: int = 4,
) -> dict:
    """Строит Complex Steerable Pyramid."""
    import pyrtools as pt

    img = image.astype(np.float32)

    pyr = pt.pyramids.SteerablePyramidFreq(
        img,
        height=levels,
        order=orientations - 1,
        is_complex=True,
    )

    result = {
        "lowpass": None,
        "highpass": None,
        "bands": {},
    }

    for key, coeff in pyr.pyr_coeffs.items():
        if isinstance(key, tuple):
            level, orient = key
            result["bands"][(level, orient)] = np.asarray(coeff)
        elif key == "residual_lowpass":
            result["lowpass"] = np.asarray(coeff)
        elif key == "residual_highpass":
            result["highpass"] = np.asarray(coeff)

    return result


def split_real_imag(complex_coeff: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.real(complex_coeff), np.imag(complex_coeff)


def reconstruct_from_bands(
    bands: dict,
    lowpass: np.ndarray,
    highpass: np.ndarray | None,
    levels: int,
    orientations: int,
    output_size: tuple[int, int],
) -> np.ndarray:
    """Собирает Y из коэффициентов пирамиды."""
    import pyrtools as pt

    orig_h, orig_w = output_size

    pyr = pt.pyramids.SteerablePyramidFreq(
        image=np.zeros((orig_h, orig_w), dtype=np.float32),
        height=levels,
        order=orientations - 1,
        is_complex=True,
    )

    pyr_coeffs = {}
    if highpass is not None:
        pyr_coeffs["residual_highpass"] = highpass
    pyr_coeffs["residual_lowpass"] = lowpass
    for (level, orient), coeff in bands.items():
        pyr_coeffs[(level, orient)] = coeff

    pyr.pyr_coeffs = pyr_coeffs
    y = pyr.recon_pyr()

    return np.asarray(y, dtype=np.float32)