# Мониторинг состояния виброгасителей, изоляторов и траверсов ЛЭП

Решение для автоматизированного анализа состояния критически важных элементов линий электропередачи на основе компьютерного зрения.

## Архитектура

Микросервисная архитектура (монорепозиторий):

```
┌─────────────────┐
│  Frontend       │  Vue.js + Nginx (порт 8501)
│  (frontend)     │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  BFF Service    │  FastAPI Gateway (порт 8000)
│  (bff-service)  │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  YOLOv8 Model   │  FastAPI + YOLOv8 (порт 8001)
│  (model-service)│
└─────────────────┘
```

## Структура проекта (Монорепозиторий)

```
MonitoringTheConditionOfVibrationDampers/
├── data_preparation/          # Скрипты подготовки данных (в корне)
│   ├── convert_coco_to_yolo.py
│   └── split_dataset.py
├── dataset/                   # Подготовленные данные (в корне)
│   ├── images/               # train/val/test
│   ├── labels/               # train/val/test
│   └── dataset.yaml
├── notebooks/                 # Jupyter notebooks (в корне)
│   └── train_yolov8.ipynb
├── models/                    # Обученные модели
│   └── best.pt
│
├── frontend-service/          # Vue.js фронтенд
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── style.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── README.md
│
├── bff-service/               # API Gateway (Backend for Frontend)
│   ├── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── yolov8-model-service/      # Микросервис с моделью YOLOv8
│   ├── main.py
│   ├── predictor.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── docker-compose.yml         # Оркестрация всех сервисов
├── Makefile                  # Удобные команды для управления
└── README.md
```

## Быстрый старт

### 1. Подготовка данных (локально)

```bash
# Из корня проекта
python data_preparation/convert_coco_to_yolo.py
python data_preparation/split_dataset.py
```

### 2. Обучение модели (Google Colab)

См. `notebooks/train_yolov8.ipynb` и `NEXT_STEPS.md`

### 3. Запуск всех сервисов (Docker Compose)

```bash
# Убедитесь, что модель в models/best.pt
docker-compose up --build

# Или используйте Makefile
make build
make up
```

Сервисы будут доступны:
- **Frontend**: http://localhost:8501
- **BFF API**: http://localhost:8000
- **Model Service**: http://localhost:8001

**Управление через Makefile:**
```bash
make build    # Собрать образы
make up       # Запустить сервисы
make down     # Остановить сервисы
make logs     # Показать логи
make restart  # Перезапустить
```

### 4. Запуск отдельных сервисов (для разработки)

**Frontend (Vue.js):**
```bash
cd frontend-service
npm install
npm run dev
```
Откроется на http://localhost:5173

**BFF:**
```bash
cd bff-service
pip install -r requirements.txt
python main.py
```

**Model Service:**
```bash
cd yolov8-model-service
pip install -r requirements.txt
python main.py
```

## API Endpoints

### BFF Service (http://localhost:8000)

- `GET /` - информация о сервисе
- `GET /health` - проверка здоровья
- `POST /predict?conf=0.25` - детекция объектов (параметр `conf` - порог уверенности 0.0-1.0)

### YOLOv8 Model Service (http://localhost:8001)

- `GET /health` - проверка здоровья
- `POST /predict?conf=0.25` - детекция объектов

## Технологии

- **Модель**: YOLOv8 (Ultralytics)
- **Frontend**: Vue.js 3 + Vite
- **BFF**: FastAPI
- **Model Service**: FastAPI + YOLOv8
- **Оркестрация**: Docker Compose
- **Обучение**: Google Colab

## Функции

### Frontend (Vue.js)
- ✅ Загрузка изображений (drag & drop)
- ✅ Визуализация bounding boxes на изображении с цветовой кодировкой
- ✅ Настройка порога уверенности через слайдер
- ✅ Статистика по категориям объектов
- ✅ Фильтрация детекций по классам
- ✅ Предупреждения о дефектах
- ✅ Адаптивный дизайн

### Backend
- ✅ Логирование всех запросов
- ✅ Валидация размера файлов (макс 50MB)
- ✅ Обработка ошибок с понятными сообщениями
- ✅ Health checks для всех сервисов
- ✅ Настройка порога уверенности через API параметр

## Метрики

Целевая метрика: **mAP@0.5 ≥ 0.7** (идеально ≥ 0.85)
