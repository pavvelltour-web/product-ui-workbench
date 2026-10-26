# Зависимости и работа без них

## Минимум: только навык

Установите всю папку навыка и вызовите его в Codex/Claude Code. Для инструкций, разборов и написания промптов Python не нужен. Для визуальной оценки агенту нужен способ действительно просмотреть изображение.

Поиск и библиотеки экранов не входят в навык. Подходит любой доступный поиск или свои разрешённые скриншоты. Порядок выбора источников: [REFERENCE_SEARCH.md](REFERENCE_SEARCH.md).

## Локальные команды

Python 3.10+ — для CLI, каталогов, хешей, проверок и установщика. Базовые команды используют стандартную библиотеку, `pip install` для них не нужен.

```bash
python --version
python scripts/pipeline.py --workspace /path/to/existing-workspace --help
```

На Windows команда Python может называться `py -3`, на macOS/Linux — `python3`. Подставляйте команду своей установки во все примеры.

## Настоящие браузерные PNG — необязательная ветка

Если вы решили включить этот путь, создайте отдельное окружение и установите зафиксированную зависимость:

```bash
python -m venv .venv
# Активируйте .venv для своей оболочки, затем:
python -m pip install -r requirements-render.txt
```

Используйте уже установленный Chrome/Chromium и передавайте полный путь через `--chrome`. Другой вариант — явно установить Chromium для Playwright:

```bash
python -m playwright install chromium
python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print(p.chromium.executable_path); p.stop()"
```

Полученный путь передайте в `demo.py --chrome` или `render_web.py --chrome`. Совместимость версий и установку системных пакетов смотрите в [официальной инструкции Playwright](https://playwright.dev/python/docs/browsers). Команда установки браузера скачивает дополнительные файлы; навык и его installer её автоматически не выполняют.

Тесты ищут существующий браузер или читают `WORKBENCH_CHROME`:

```powershell
$env:WORKBENCH_CHROME = 'C:/path/to/chrome.exe'
python -m unittest discover -s tests -v
```

```bash
WORKBENCH_CHROME=/path/to/chromium python -m unittest discover -s tests -v
```

Без Playwright/браузера соответствующие тесты показывают `skipped`. Это не выполненная браузерная проверка.

## UI-библиотеки — отдельный выбор

Native HTML/CSS/JS и компоненты `library/components/native-workbench.mjs` не требуют Node.js. Для React/shadcn нужен совместимый проект, его пакеты, CSS-токены и сборка. Смотрите [API сохранённых компонентов](../library/components/react-shadcn/API.md), [dependency baseline](../library/components/react-shadcn/dependencies.json) и [официальную установку](https://ui.shadcn.com/docs/installation).

Нет универсальной команды, которая безопасно добавляет React/Tailwind/Radix в любой чужой проект. Сначала проверяются его версии, сборка и уже существующие компоненты. Native-реализация допустима, но её нельзя называть реализацией shadcn.

Одна дополнительная проверка математических функций React-примера использует уже установленный Node.js. Без него она показывает `skipped`; Python-инструменты и нативный демо-интерфейс Node.js не требуют.
