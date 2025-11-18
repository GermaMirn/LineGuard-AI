# YOLOv8 Model Service

Микросервис для детекции элементов ЛЭП на основе YOLOv8.

## Описание

Сервис загружает обученную модель YOLOv8 и предоставляет API для детекции объектов на изображениях.

## Структура проекта

```
yolov8-model-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # Главный файл приложения
│   ├── api/
│   │   ├── __init__.py
│   │   └── predict.py       # API роутеры для предсказаний
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Настройки сервиса
│   ├── services/
│   │   ├── __init__.py
│   │   └── predictor.py     # Сервис для работы с YOLOv8 моделью
│   └── schemas/
│       ├── __init__.py
│       └── predict.py       # Pydantic схемы для API
├── Dockerfile
├── requirements.txt
└── README.md
```

## API

- `GET /` - информация о сервисе
- `GET /health` - проверка здоровья сервиса
- `GET /model/info` - информация о модели (метрики, классы)
- `POST /predict` - детекция объектов на изображении

## Запуск

### Docker

```bash
docker-compose up yolov8-model-service
```

### Локально

```bash
pip install -r requirements.txt
export MODEL_PATH=../models/best.pt
python -m app.main
```

## Переменные окружения

- `MODEL_PATH` - путь к модели (по умолчанию: `/app/models/best.pt`)
- `PORT` - порт сервиса (по умолчанию: `8000`)
- `DEFAULT_CONF_THRESHOLD` - порог уверенности по умолчанию (по умолчанию: `0.25`)

## Поддерживаемые форматы

- Стандартные: JPG, PNG, TIFF
- RAW форматы дронов: DNG, RAW, CR2, NEF, ARW

## Классы объектов

1. `vibration_damper` - Виброгаситель
2. `festoon_insulators` - Гирлянда изоляторов
3. `traverse` - Траверса
4. `bad_insulator` - Изолятор отсутствует (дефект)
5. `damaged_insulator` - Поврежденный изолятор (дефект)
6. `polymer_insulators` - Полимерные изоляторы
