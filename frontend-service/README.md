# Frontend Service (React)

Веб-интерфейс для мониторинга ЛЭП на React + TypeScript.

## Технологии

- **React 19** - фреймворк
- **TypeScript** - типизация
- **Vite** - сборщик
- **Hero UI KIT** - UI компоненты
- **Zustand** - state management
- **Axios** - HTTP клиент
- **React Query** - управление серверным состоянием
- **Nginx** - веб-сервер (в production)

## Разработка

### Установка зависимостей

```bash
npm install
```

### Запуск dev сервера

```bash
npm run dev
```

Приложение будет доступно на http://localhost:5173

### Сборка для production

```bash
npm run build
```

## Docker

### Сборка образа

```bash
docker build -t lep-frontend .
```

### Запуск контейнера

```bash
docker run -p 8501:80 lep-frontend
```

### Через docker-compose

```bash
docker-compose up frontend-service
```

## Переменные окружения

- `VITE_BFF_SERVICE_URL` - URL BFF Service (по умолчанию: `/api`)

## Функции

- ✅ Загрузка изображений (drag & drop или выбор файла)
- ✅ Отправка запросов к BFF API
- ✅ Отображение результатов детекции
- ✅ Статистика по категориям
- ✅ Фильтрация детекций
- ✅ Предупреждения о дефектах
- ✅ Отрисовка bounding boxes на изображении
