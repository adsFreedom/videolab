Project: VideoLab - Визуальный пайплайн обработки видео
Общая концепция:
VideoLab — это десктопное приложение на Python/PySide6 для построения пайплайнов обработки видео. Пользователь загружает исходное видео, затем создает цепочку обработчиков (узлов), каждый из которых преобразует данные и сохраняет результаты в физические папки на диске. Приложение работает как файловый менеджер с расширенной логикой валидации и обработки.

1. Файловая структура проекта
```text
~/VideoLab_Projects/                  # Корневая папка со всеми проектами
└── MyProject/                        # Конкретный проект (пользователь создает вручную)
    ├── .videolab                     # Файл метаданных проекта (YAML)
    ├── source_0/                     # Корневая папка с исходным видео
    │   ├── source_0.yaml             # Настройки корня (пустой или с метаданными)
    │   └── video_001.avi             # Исходный видеофайл
    │
    ├── crop_1/                       # Первый обработчик (прямой потомок корня)
    │   ├── crop_1.yaml               # Настройки + поле input_file (абсолютный путь)
    │   ├── output_001.avi            # Результат обработки
    │   └── output_001_metadata.yaml  # Технические данные (опционально)
    │
    ├── gaussian_2/                   # Второй обработчик (тоже потомок корня)
    │   ├── gaussian_2.yaml
    │   └── blurred_001.avi
    │
    └── crop_3/                       # Третий обработчик (рядом с первыми)
        ├── crop_3.yaml
        └── output_001.avi
```        
Важные правила:

Каждый узел — это папка.

Имя папки формируется как {processor_name}_{counter} (счетчик внутри родительской папки, начинается с 1, если удалить crop_1, следующий будет снова crop_1).

В папке обязательно должен быть YAML-файл с настройками.

YAML-файл содержит поле input_file — абсолютный путь к обрабатываемому файлу.

Результаты обработки сохраняются в той же папке с фиксированными именами по маске (например, output_*.avi).

2. Архитектура приложения (MVVM)
```text
┌─────────────────────────────────────────────────────────┐
│  VIEW (PySide6 Widgets)                               │
│  - MainWindow (QSplitter: TreeView | Settings/Viewer) │
│  - TreeView (QTreeView с кастомной моделью)           │
│  - ProcessorDialog (QDialog: выбор файла + настройки) │
│  - Viewer widgets (Image, Video, Text)                │
│  - ProgressDialog (QProgressDialog)                   │
└──────────────────────┬──────────────────────────────────┘
                       │ Signals/Slots
┌──────────────────────▼──────────────────────────────────┐
│  VIEWMODEL (Controller)                                │
│  - ProjectController (синглтон)                       │
│  - Содержит ссылку на ProjectManager                  │
│  - Обрабатывает сигналы от UI                         │
│  - Управляет состоянием (текущий выбранный узел)     │
└──────────────────────┬──────────────────────────────────┘
                       │ Method calls
┌──────────────────────▼──────────────────────────────────┐
│  MODEL (Business Logic)                                │
│  - ProjectManager - работа с файловой системой        │
│  - ProcessorRegistry - регистрация обработчиков       │
│  - BaseProcessor - базовый класс для обработчиков    │
│  - ViewerRegistry - регистрация просмотрщиков         │
└─────────────────────────────────────────────────────────┘
```
3. Основные компоненты системы
A. ProjectManager (Ядро)
Отвечает за:

Сканирование папки проекта и построение дерева.

Создание новых узлов-обработчиков.

Валидацию узлов (проверка наличия выходных файлов).

Чтение/запись YAML-конфигов.

Ключевые методы:

```python
class ProjectManager:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.processors = ProcessorRegistry()
    
    def get_tree(self) -> dict:
        """Возвращает дерево проекта в виде словаря {path: [children]}"""
        pass
    
    def get_node_info(self, node_path: str) -> dict:
        """Читает YAML и возвращает информацию об узле"""
        pass
    
    def create_processor_node(self, parent_path: str, processor_name: str, 
                              input_file: str, settings: dict) -> str:
        """
        Создает новый узел-обработчик:
        1. Находит следующий доступный номер (processor_name_N)
        2. Создает папку
        3. Сохраняет YAML с настройками и input_file
        4. Возвращает путь к новому узлу
        """
        pass
    
    def validate_node(self, node_path: str) -> tuple[bool, str]:
        """
        Проверяет узел:
        - Существует ли папка?
        - Есть ли YAML?
        - Есть ли выходные файлы по маске из обработчика?
        - Если нет - возвращает (False, "причина")
        """
        pass
    
    def scan_for_inputs(self, start_path: str, mask: str) -> list[str]:
        """
        Сканирует папку start_path и все родительские папки вверх до корня
        Возвращает список файлов, подходящих под маску (абсолютные пути)
        """
        pass
```
B. BaseProcessor (Обработчик)
Базовый класс для всех обработчиков:

```python
class BaseProcessor:
    # Обязательные атрибуты
    name: str = "processor_name"           # Уникальное имя
    display_name: str = "Название в меню"   # Для отображения в UI
    input_mask: str = "*.avi"              # Маска для входных файлов
    output_mask: str = "output_*.avi"      # Маска для выходных файлов
    
    # Схема настроек (JSON Schema)
    settings_schema: dict = {
        "param1": {
            "type": "spinbox",           # spinbox | double_spinbox | checkbox | lineedit | combobox
            "label": "Параметр 1",
            "default": 10,
            "min": 0,
            "max": 100,
            "step": 1
        }
    }
    
    def run(self, input_file: str, settings: dict, output_dir: str) -> dict:
        """
        Основная функция обработки.
        - input_file: абсолютный путь к входному файлу
        - settings: словарь с настройками (из YAML)
        - output_dir: папка, куда сохранять результаты
        
        Возвращает словарь с информацией о результатах:
        {
            "output_files": ["output_001.avi", ...],
            "metadata": {"frames": 100, "fps": 30}
        }
        """
        raise NotImplementedError()
```
Пример обработчика:

```python
class CropProcessor(BaseProcessor):
    name = "crop"
    display_name = "Обрезка видео"
    input_mask = "*.avi"
    output_mask = "crop_*.avi"
    
    settings_schema = {
        "start_frame": {"type": "spinbox", "label": "Начальный кадр", "default": 0, "min": 0},
        "end_frame": {"type": "spinbox", "label": "Конечный кадр", "default": 100, "min": 0}
    }
    
    def run(self, input_file, settings, output_dir):
        # Используем moviepy или OpenCV для обрезки
        pass
```
C. ProcessorDialog (Диалог создания обработчика)
Диалог появляется при выборе обработчика из контекстного меню.

Структура диалога:

```text
┌─────────────────────────────────────────────────────┐
│  Создание обработчика: Crop                        │
├─────────────────────────────────────────────────────┤
│  Выбор входного файла:                             │
│  [ComboBox с файлами по маске]                    │
│                                                     │
│  Настройки:                                        │
│  [Начальный кадр] [SpinBox]                       │
│  [Конечный кадр]  [SpinBox]                       │
│                                                     │
│  [Отмена]  [Запустить]                            │
└─────────────────────────────────────────────────────┘
```
D. TreeModel (QAbstractItemModel)
Кастомная модель для QTreeView.

Особенности:

Модель НЕ хранит данные в памяти, а читает файловую систему при каждом запросе.

Каждый узел — это путь к папке.

Корень проекта — это папка проекта (например, ~/VideoLab_Projects/MyProject).

Только папки, содержащие YAML, отображаются как узлы.

Цвет текста: черный (валидный), красный (невалидный).

Методы:

```python
class TreeModel(QAbstractItemModel):
    def __init__(self, project_manager):
        self.project = project_manager
        self.root_path = project_manager.project_root
    
    def index(self, row, column, parent):
        # Возвращает QModelIndex для строки/колонки
        pass
    
    def parent(self, index):
        # Возвращает родительский индекс
        pass
    
    def rowCount(self, parent):
        # Количество дочерних узлов (папок с YAML)
        pass
    
    def data(self, index, role):
        # Qt.DisplayRole: имя папки
        # Qt.ForegroundRole: цвет (красный если невалидный)
        pass
```
E. ViewerRegistry (Просмотрщики)
Регистрация просмотрщиков для разных типов файлов:

```python
class ViewerRegistry:
    _viewers = {}
    
    @classmethod
    def register(cls, extension, viewer_class):
        cls._viewers[extension] = viewer_class
    
    @classmethod
    def get_viewer(cls, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        viewer_class = cls._viewers.get(ext, TextViewer)
        return viewer_class(file_path)
```
Базовые просмотрщики для MVP:

.avi, .mp4 → VideoViewer (QMediaPlayer)

.jpg, .jpeg, .png, .bmp → ImageViewer (QLabel с QPixmap)

.txt, .yaml, .json, .log → TextViewer (QTextEdit)

.npy → NumpyViewer (QTableWidget с данными)

4. Пользовательский сценарий (User Flow)
Загрузка/создание проекта:
При запуске приложения открывается диалог выбора папки проекта.

Если в папке есть .videolab — загружаем проект.

Если нет — создаем новый проект (создаем .videolab и корневую папку source_0).

Работа с деревом:
Пользователь видит дерево проекта в левой панели.

Корень — папка с исходным видео (например, source_0).

Клик по узлу → справа отображаются настройки узла (YAML) и список файлов в этой папке.

Двойной клик по файлу → открывается просмотрщик для этого типа файла.

Создание обработчика:
ПКМ по узлу → контекстное меню со списком доступных обработчиков.

Доступные = те, чей input_mask совпадает с хотя бы одним файлом в текущей папке.

Выбор обработчика → открывается ProcessorDialog.

В диалоге:

ComboBox со списком файлов (по маске).

JSON-форма с настройками (генерируется из settings_schema).

Нажатие "Запустить":

Создается новый узел (папка + YAML).

Запускается обработка (синхронно, в отдельном потоке? НЕТ! Пока синхронно с модальным окном).

После завершения — дерево обновляется.

Валидация узлов:
При загрузке проекта или после создания узла запускается валидация.

Узел считается валидным, если:

Папка существует.

Есть YAML-файл.

В папке есть хотя бы один файл, подходящий под output_mask обработчика.

Если невалидный — узел в дереве подсвечивается красным.

5. TODO-план (MVP)
Фаза 0: Подготовка (День 1)
□ Создать структуру папок проекта.
□ Настроить виртуальное окружение Python.
□ Установить зависимости:
bash
pip install PySide6 PyYAML opencv-python moviepy numpy
Фаза 1: Ядро и файловая система (День 1-2)
□ Создать класс ProjectManager.
□ __init__ (принимает путь к проекту).
□ get_tree() — сканирует папки и строит дерево.
□ get_node_info(path) — читает YAML.
□ create_processor_node(parent_path, processor_name, input_file, settings).
□ validate_node(path) — проверяет наличие выходных файлов.
□ scan_for_inputs(start_path, mask) — поиск файлов по маске вверх по дереву.
□ get_next_counter(parent_path, processor_name) — вычисляет следующий номер.
Фаза 2: Обработчики (День 2-3)
□ Создать базовый класс BaseProcessor.
□ Создать ProcessorRegistry (регистрация и получение обработчиков).
□ Написать 2-3 тестовых обработчика:
□ ConvertToGray (конвертация видео в черно-белое).
□ CropProcessor (обрезка видео по кадрам).
□ ExtractFrames (извлечение кадров в картинки).
Фаза 3: GUI — Дерево проекта (День 3-4)
□ Создать MainWindow (QSplitter: TreeView | StackedWidget).
□ Создать TreeModel (наследник QAbstractItemModel).
□ Читает дерево из ProjectManager.
□ Отображает имена папок.
□ Меняет цвет (валидный/невалидный).
□ Создать TreeView с контекстным меню.
□ ПКМ → получаем список доступных обработчиков (фильтр по input_mask).
□ При выборе обработчика — открываем ProcessorDialog.
Фаза 4: GUI — Диалог создания обработчика (День 4-5)
□ Создать ProcessorDialog (QDialog).
□ ComboBox с файлами из scan_for_inputs().
□ Динамическая генерация настроек из settings_schema.
□ Кнопки "Отмена" / "Запустить".
□ При нажатии "Запустить":
Создать узел через ProjectManager.

Запустить processor.run().

Показать модальное окно прогресса (синхронно).

Обновить дерево.

Фаза 5: GUI — Просмотрщики (День 5-6)
□ Создать ViewerRegistry.
□ Написать базовые просмотрщики:
□ ImageViewer (QLabel с масштабированием).
□ VideoViewer (QMediaPlayer).
□ TextViewer (QTextEdit).
□ NumpyViewer (QTableWidget).
□ При клике на узел — справа показывать список файлов в папке.
□ При двойном клике по файлу — открывать просмотрщик в новой вкладке/окне.
Фаза 6: Интеграция и тестирование (День 6-7)
□ Связать все компоненты.
□ Добавить обработку ошибок (проверка существования файлов, прав доступа).
□ Добавить кнопку "Обновить" для пересканирования проекта.
□ Написать тесты (pyTest) для ProjectManager.
□ Создать README.md с инструкцией по установке и использованию.
6. Важные технические решения (Trade-offs)
Решение	Почему
Синхронная обработка с модальным окном	Проще реализовать, меньше багов с потоками на старте.
Хранение абсолютных путей в YAML	Позволяет точно знать, откуда взяты данные.
Нет глобального счетчика	Счетчик внутри папки проще для понимания пользователя.
YAML вместо GUI для настроек	Быстрая разработка, не нужно писать GUI для каждого обработчика.
Модель дерева без кэширования	Проще реализовать, гарантирует актуальность данных.
7. Пример YAML-файла узла
```yaml
# crop_1.yaml
processor: "crop"
input_file: "/home/user/VideoLab_Projects/MyProject/source_0/video_001.avi"
settings:
  start_frame: 10
  end_frame: 150
created: "2026-08-31 14:30:00"
output_files:
  - "output_001.avi"
  - "output_001_thumb.jpg"
```
8. Расширение в будущем (После MVP)
□ Асинхронная очередь обработки (QThreadPool).
□ Drag-and-Drop для добавления файлов.
□ Экспорт проекта в ZIP.
□ Откат к предыдущим версиям узлов (история).
□ Плагины (загрузка обработчиков из папки plugins/).
□ Поддержка GPU (CUDA).
□ Визуальный нодовый редактор.