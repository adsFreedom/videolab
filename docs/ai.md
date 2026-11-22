PROJECT SUMMARY: VideoLab
🎯 Что это
VideoLab — десктопное приложение на Python + PySide6 для построения модульных пайплайнов обработки видео, изображений и numpy-данных. Пользователь загружает видео, затем последовательно применяет обработчики (обрезка, FFT, детекция лиц, ROI и т.д.), каждый из которых сохраняет результаты в отдельную физическую папку. Работает как файловый менеджер с расширенной логикой валидации и обработки.

Ключевая идея: каждый шаг обработки = отдельная папка с настройками (YAML) и результатами. Пайплайн — это дерево папок.

🏗️ Технологический стек
Язык: Python 3.10+

GUI: PySide6 (Qt6)

Архитектура: MVVM (Model-View-ViewModel)

Хранение метаданных: YAML

Обработка видео: OpenCV (cv2), NumPy (позже: moviepy, mediapipe)

Сборка: pyinstaller (на будущее)

Тестирование: pytest

📁 Файловая структура проекта
```text
~/VideoLab_Projects/                  # Корневая папка со всеми проектами
└── MyProject/                        # Конкретный проект
    ├── .videolab                     # Метаданные проекта (YAML)
    ├── source_0/                     # Корневая папка (исходное видео)
    │   ├── source_0.yaml
    │   └── video.avi
    │
    ├── crop_1/                       # Обработчик (потомок source_0)
    │   ├── crop_1.yaml               # Настройки + input_file (абсолютный путь)
    │   └── output_001.avi
    │
    └── detect_face_2/                # Обработчик (потомок source_0)
        ├── detect_face_2.yaml
        ├── faces.npy
        │
        ├── roi_forehead_3/           # Под-обработчик (потомок detect_face_2)
        │   ├── roi_forehead_3.yaml
        │   └── forehead_frames.npy
        │
        └── roi_nose_4/               # Ещё один под-обработчик
            └── ...
```            
Правила именования:
Имя папки: {processor_name}_{counter}.

Счетчик внутри родительской папки, начинается с 1.

Если папка crop_1 удалена, следующий обработчик тоже будет crop_1.

Каждая папка содержит YAML-файл с тем же именем.

YAML-структура узла (пример):
```yaml
# crop_1.yaml
processor: "crop"
display_name: "Обрезка видео"
input_file: "/home/user/VideoLab_Projects/MyProject/source_0/video.avi"
settings:
  start_frame: 10
  end_frame: 150
created: "2026-09-15 14:30:00"
expected_outputs:
  - output_001.avi
```
🔗 Логика поиска входных файлов (КРИТИЧНО!)
Правило: обработчик, созданный внутри узла, может брать входные файлы из папки этого узла И из папок всех родителей вверх по дереву (до корня проекта).

Пример:

Пользователь кликнул ПКМ на detect_face_2/ и выбрал обработчик RelativeROI.

Обработчик ищет файлы по маске (например, *.avi и faces.npy).

Сначала смотрит в detect_face_2/ — находит faces.npy.

Потом идет в source_0/ — находит video.avi.

В ProcessorDialog показываются оба файла, пользователь выбирает.

Это реализуется через ProjectManager.scan_for_inputs(start_path, mask).

🎨 UI/UX (финальный дизайн)
Структура окна:
```text
┌──────────────────────────────────────────────────────────────────────┐
│  🎬 VideoLab  —  Проект: MyProject  □  ✕                          │
│  [🎥 Записать] [📂 Открыть] [🔄 Обновить] [👤 Пользователь]      │
├──────────────────────────────────────────────────────────────────────┤
│  📁 ДЕРЕВО  │  ⚙️ НАСТРОЙКИ / 📊 ДАННЫЕ  │  📄 ФАЙЛЫ/ПРЕВЬЮ       │
│   (25%)     │          (45%)              │        (30%)           │
│             │                             │                        │
│  ▼ source_0 │  [⚙️ Настройки] [📊 Данные]│  📂 crop_1           │
│   ▼ crop_1  │  Обработчик: Crop           │  ├─ 📹 output_001.avi │
│   ▼ face_2  │  Вход: [▼ video.avi]        │  ├─ 🖼️ thumb.jpg      │
│    ├─ roi_3 │  Нач. кадр: [10]           │  └─ 📄 meta.yaml      │
│    └─ roi_4 │  Кон. кадр: [150]          │                        │
│             │  [🔄 Применить] [⏹ Сброс] │  ─ ПРЕВЬЮ ─          │
├──────────────────────────────────────────────────────────────────────┤
│  [📋 Общий лог] [🔀 Сравнение видео]      [▼ Скрыть панель]      │
├──────────────────────────────────────────────────────────────────────┤
│  [14:30:22] ✅ crop_1: Обработка завершена                         │
│  [14:28:15] ❌ ERROR: Не найден video.avi                          │
└──────────────────────────────────────────────────────────────────────┘
```
Ключевые решения:
Дерево показывает ТОЛЬКО папки-обработчики (не файлы).

Файлы отображаются в правой панели.

Иконки: папка-обработчик + цвет (зеленый/красный).

Цветовая кодировка узлов:

🟢 Зеленый — валидный (все выходные файлы на месте).

🔴 Красный — невалидный (файлы отсутствуют), все потомки тоже красные.

Центральная панель — вкладки:

⚙️ Настройки (JSON-форма обработчика).

📊 Данные (статистика узла).

Правая панель:

Список файлов в текущей папке.

Просмотрщик (видео — встроенный, картинки/текст — отдельные окна).

Нижняя панель — вкладки:

📋 Общий лог — с цветовой индикацией:

Ошибка → вкладка горит красным 🔴.

Предупреждение → желтым 🟡.

При переходе на вкладку цвет сбрасывается.

🔀 Сравнение видео — 4 режима: рядом, сплит (двигаемая полоса), разница, наложение.

Горячие клавиши: Ctrl+N (новый), F2 (переименовать), F5 (обновить), Ctrl+Enter (применить), Ctrl+L (лог).

Темы: темная / светлая.

Сохранение состояния через QSettings (размеры сплиттеров, последний узел, тема).

🧩 Архитектура ядра
MVVM-слои:
```text
┌─────────────────────────────────────────────────┐
│  VIEW (PySide6 Widgets)                        │
│  - MainWindow, TreeView, SettingsPanel,        │
│    FilesPanel, LogWidget, CompareWidget,       │
│    ProcessorDialog, Viewers                    │
└──────────────────┬──────────────────────────────┘
                   │ Signals/Slots
┌──────────────────▼──────────────────────────────┐
│  VIEWMODEL (Controller)                        │
│  - ProjectController (синглтон)                │
│  - Управляет состоянием UI                     │
└──────────────────┬──────────────────────────────┘
                   │ Method calls
┌──────────────────▼──────────────────────────────┐
│  MODEL (Business Logic)                        │
│  - ProjectManager (файловая система)           │
│  - ProcessorRegistry (регистрация)             │
│  - BaseProcessor (базовый класс)               │
│  - ViewerRegistry (просмотрщики)               │
└─────────────────────────────────────────────────┘
```
Ключевые классы:
1. ProjectManager
```python
class ProjectManager:
    def __init__(self, project_root: str): ...
    
    def get_tree(self) -> dict: ...
    def get_node_info(self, node_path: str) -> dict: ...
    def create_processor_node(self, parent_path, processor_name, 
                              input_files: dict, settings: dict) -> str: ...
    def validate_node(self, node_path: str) -> tuple[bool, str]: ...
    def scan_for_inputs(self, start_path: str, mask: str) -> list[str]: ...
    def get_next_counter(self, parent_path, processor_name) -> int: ...
```    
2. BaseProcessor
```python
class BaseProcessor:
    name: str = "processor_name"
    display_name: str = "Название"
    
    # Multi-input: словарь {логическое_имя: {mask, required}}
    input_spec: dict = {
        "video": {"mask": "*.avi", "required": True},
        "coords": {"mask": "faces.npy", "required": False}
    }
    
    # Multi-output: список ожидаемых файлов
    output_mask: str = "output_*.avi"
    expected_outputs: list = None  # Или список конкретных файлов
    
    # Схема настроек (JSON)
    settings_schema: dict = {
        "param1": {"type": "spinbox", "label": "...", "default": 10, "min": 0}
    }
    
    def run(self, input_files: dict, settings: dict, output_dir: str) -> dict:
        """
        input_files = {"video": "/path/to/video.avi", "coords": "/path/to/faces.npy"}
        Возвращает: {"output_files": [...], "metadata": {...}}
        """
        raise NotImplementedError()
```        
Типы полей в settings_schema:

spinbox — целое число.

double_spinbox — дробное число.

checkbox — галочка.

lineedit — текст.

combobox — выпадающий список.

multiselect — множественный выбор (позже).

roi_relative — 4 слайдера в процентах (позже).

roi_selector — визуальный выбор области (позже).

3. ProcessorRegistry
```python
class ProcessorRegistry:
    _processors = {}
    
    @classmethod
    def register(cls, processor_class): ...
    
    @classmethod
    def get(cls, name) -> BaseProcessor: ...
    
    @classmethod
    def get_available_for(cls, node_path, project_manager) -> list[BaseProcessor]:
        # Возвращает обработчики, у которых есть подходящие входные файлы
        pass
```        
4. ViewerRegistry
```python
class ViewerRegistry:
    _viewers = {}
    
    @classmethod
    def register(cls, extensions: list, viewer_class): ...
    
    @classmethod
    def get_viewer(cls, file_path) -> QWidget: ...
```    
Зарегистрированные просмотрщики:

.avi, .mp4, .mov → VideoViewer (QMediaPlayer, встроенный).

.jpg, .png, .bmp → ImageViewer (отдельное окно).

.txt, .yaml, .json, .log → TextViewer (отдельное окно, подсветка синтаксиса).

.npy → NumpyViewer (отдельное окно, тепловая карта / график / слайдер по осям).

5. ProjectController (ViewModel)
```python
class ProjectController(QObject):
    project_loaded = Signal()
    node_selected = Signal(str)  # node_path
    log_added = Signal(str, str)  # level, message
    
    def __init__(self, project_manager): ...
    
    def load_project(self, path): ...
    def create_processor(self, parent_path, processor_name, 
                         input_files, settings): ...
    def select_node(self, node_path): ...
```    
📋 TODO-ПЛАН РЕАЛИЗАЦИИ
Phase 0: Подготовка (День 1)
□ Создать структуру папок проекта:
```text
videolab/
├── core/           # Ядро (не зависит от PySide6)
│   ├── project_manager.py
│   ├── base_processor.py
│   ├── processor_registry.py
│   ├── viewer_registry.py
│   └── utils.py
├── desktop/        # PySide6 UI
│   ├── main_window.py
│   ├── tree_model.py
│   ├── panels/
│   ├── dialogs/
│   ├── viewers/
│   └── widgets/
├── processors/     # Обработчики (плагины)
├── tests/
└── main.py
```

```
□ Виртуальное окружение: python -m venv venv.
□ Установить: PySide6 PyYAML opencv-python numpy.
□ Настроить requirements.txt.
Phase 1: Ядро без UI (День 1-2)
□ ProjectManager:
□ __init__, get_tree(), get_node_info().
□ create_processor_node() — создание папки + YAML.
□ validate_node() — проверка выходных файлов.
□ scan_for_inputs() — поиск файлов вверх по дереву.
□ get_next_counter().
□ BaseProcessor + ProcessorRegistry.
□ ViewerRegistry.
□ Тесты (pytest): создание узлов, валидация, сканирование.
□ Проверка: создать проект вручную, запустить тесты, убедиться, что YAML корректно создается.
Phase 2: UI-каркас (День 3-4)
□ MainWindow:
□ Toolbar (Записать, Открыть, Обновить).
□ 3-панельный QSplitter.
□ Нижняя панель с вкладками (QTabWidget).
□ Статус-бар.
□ TreeModel (QAbstractItemModel):
□ Отображает ТОЛЬКО папки с YAML.
□ Иконки по типу обработчика.
□ Цветовая кодировка (зеленый/красный).
□ FilesPanel:
□ Список файлов в текущей папке.
□ Иконки по типу файла.
□ LogWidget:
□ Цветовая индикация вкладки (красный/желтый).
□ Сброс цвета при переходе.
□ Проверка: открыть проект, увидеть дерево, кликнуть на узел, увидеть файлы.
Phase 3: Создание обработчиков (День 5-6)
□ ProcessorDialog:
□ Multi-input ComboBox-ы (по одному на каждый вход).
□ Динамическая генерация настроек из settings_schema.
□ Кнопки "Отмена" / "Запустить".
□ Контекстное меню (ПКМ на узле):
□ Динамический список обработчиков (фильтр по input_spec).
□ Открытие ProcessorDialog.
□ Логика запуска:
□ Создать узел через ProjectManager.
□ Запустить processor.run() синхронно.
□ Модальный прогресс-диалог.
□ Обновить дерево.
□ Проверка: создать обработчик, увидеть новую папку, проверить YAML.
Phase 4: Тестовые обработчики (День 6-7)
□ CropProcessor — обрезка видео по кадрам.
□ ConvertToGrayProcessor — черно-белое видео.
□ ExtractFramesProcessor — извлечение кадров в PNG.
□ Проверка всех обработчиков через UI.
Phase 5: Просмотрщики (День 8)
□ VideoViewer (QMediaPlayer, встроенный в правую панель).
□ ImageViewer (отдельное окно, масштабирование).
□ TextViewer (отдельное окно, подсветка YAML/JSON).
□ NumpyViewer (тепловая карта / график / слайдер).
□ Клик по файлу → открытие просмотрщика.
Phase 6: Полировка (День 9-10)
□ Горячие клавиши.
□ Темная/светлая тема.
□ Сохранение состояния (QSettings).
□ Прогресс-бары в дереве.
□ Умный поиск.
□ Кнопка "Скрыть лог".
□ Сравнение видео (режим "рядом").
□ Обработка ошибок (try/except с логом).
Phase 7: Расширения (после MVP)
□ Сравнение видео (сплит, разница, наложение).
□ Сравнение картинок и текстов.
□ Визуальный ROI (ROISelectorWidget).
□ Макросы (MacroProcessor).
□ Редактор макросов.
□ Drag-and-Drop.
□ Асинхронная очередь обработки (QThreadPool).
□ Плагины (загрузка из plugins/).
Phase 8: Специализированные обработчики (после ядра)
□ DetectFaceProcessor — детекция лиц (Haar/DNN/MediaPipe).
□ RelativeROIProcessor — вырезание области относительно родителя.
□ FFTProcessor — частотный анализ.
□ SplitChannelsProcessor — R, G, B, Y.
□ TrackROIProcessor — стабилизация ROI.
```
🔧 Ключевые технические решения
Решение	Обоснование
Синхронная обработка с модальным окном	Проще для MVP. Асинхронность добавим позже.
Хранение абсолютных путей в YAML	Точно знаем, откуда взяты данные.
Счетчик внутри папки	Интуитивно понятно пользователю.
YAML вместо GUI для настроек	Быстрая разработка, JSON-форма генерируется автоматически.
Модель дерева без кэширования	Проще, гарантирует актуальность (глубина ≤ 10).
Multi-input через input_spec	Позволяет комбинировать данные из разных папок.
Иерархия: обработчик-потомок кликнутого узла	Сохраняет логическую связь в дереве.
Правило поиска: вверх по дереву	Обработчик находит видео в source_0 даже если создан в detect_face_2.
⚠️ Важные ограничения и решения
Правило "ПКМ на узле": обработчик создается внутри папки узла, на котором кликнули ПКМ.

Поиск файлов: scan_for_inputs() идет вверх по родителям до корня проекта (.videolab).

Валидация: если у узла нет выходных файлов → красный. Потомки тоже красные (каскадно).

Счётчик имён: сбрасывается при удалении (не глобальный).

Обработка ошибок: все ошибки в общий лог с уровнем ERROR.

Корень проекта: определяется по файлу .videolab.

📦 Зависимости
```text
PySide6>=6.5
PyYAML>=6.0
opencv-python>=4.8
numpy>=1.24
pytest>=7.0 (dev)
Позже (для обработчиков):

text
moviepy
mediapipe
matplotlib
scipy
```
🎯 ГЛАВНЫЕ ПРИНЦИПЫ (не нарушать!)
Ядро (core/) НЕ импортирует PySide6. UI зависит от ядра, но не наоборот.

Каждый шаг = отдельная папка с YAML и результатами.

Обработчик — самодостаточен. Он знает только о своих входах и настройках.

UI генерируется из settings_schema. Никаких хардкодных форм.

Правило "вверх по дереву" — обработчики ищут файлы у всех родителей.

Синхронная обработка в MVP. Асинхронность — потом.

Файлы — это единственный источник правды. Дерево читает диск при каждом запросе.

🚀 Что дальше
Следующий шаг: начать с Phase 1 (Ядро).

Первый код:

core/project_manager.py — ProjectManager с методами create_processor_node, validate_node, scan_for_inputs.

core/base_processor.py — BaseProcessor.

core/processor_registry.py — реестр.

Тесты.

Промпт для нового чата:

Мы разрабатываем VideoLab — приложение на Python + PySide6 для модульной обработки видео. Архитектура MVVM, ядро в core/ не зависит от PySide6. Все данные хранятся в файловой системе (YAML + результаты). Обработчики регистрируются через ProcessorRegistry, каждый обработчик — подкласс BaseProcessor с input_spec, output_mask, settings_schema. Дерево показывает только папки-обработчики. Правило поиска входных файлов — вверх по дереву до корня проекта (.videolab). Начинаем с ProjectManager. Вот полное описание проекта: [вставить саммари].

✅ Итоговый чек-лист готовности
☑ Архитектура (MVVM, ядро/UI).
☑ Файловая структура (YAML, папки).
☑ UI/UX (3 панели, вкладки, лог, сравнение).
☑ Модель обработчиков (multi-input, schema).
☑ Правило поиска (вверх по дереву).
☑ Расширения (ROI, макросы, детекция лиц) — спроектированы.
☑ TODO-план по фазам.
☑ Принципы и ограничения.