# VideoLab

Десктопное приложение на Python/PySide6 для построения пайплайнов обработки видео.
Загружаете видео → собираете цепочку процессоров → каждый узел преобразует данные
и сохраняет результат на диск. Плагинная архитектура: новый процессор подключается
через реестр без изменения ядра.

https://github.com/user-attachments/assets/f7c46012-1682-4846-b98d-c7040b421669

## Возможности
- **Амплификация движений** (`motion_magnify`, `yiq_csp`, `csp`): фазовое усиление
  микродвижений на основе steerable pyramid (pyrtools) — визуализация того, что
  глазом не заметно (вибрации, пульсация, дыхание).
- YIQ CSP и обратный процессор (`yiq_csp_inverse`)
-Crop, crop_region, resize, extract_frames, convert_to_avi
- GUI на PySide6 + pyqtgraph, валидация цепочек обработки

## Архитектура
core/        — ядро пайплайна и реестр процессоров
processors/  — процессоры (плагины)
desktop/     — UI (PySide6)
projects/    — пользовательские проекты (данные на диске)
utils/       — вспомогательные утилиты
tests/       — pytest: ядро + реальные процессоры

## Быстрый старт
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

## Тесты
pip install -r requirements-dev.txt
pytest -q

## Стек
Python · PySide6 · OpenCV · NumPy · pyrtools · pyqtgraph · pytest