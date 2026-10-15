# Карта сайта

| Страница | Файл | Содержание |
| --- | --- | --- |
| Что это | [index.md](index.md) | состав, схема, ограничения, быстрый старт |
| Установка | [install.md](install.md) | MCP, bridge.json, запуск, сборка exe, автозапуск |
| Протокол | [protocol.md](protocol.md) | конверт запроса и ответа, jsonpath, ключи, проверки |
| API скрипта | [api.md](api.md) | функции `internet-core`, шаблон обработчика, таймауты |
| Примеры | [examples.md](examples.md) | погода, POST, Gemini, Telegram, вебхуки |
| Правила для ИИ | [ai-rules.md](ai-rules.md) | инструкция для нейронки, запреты, чек-лист |
| Решение проблем | [troubleshooting.md](troubleshooting.md) | симптом → причина → действие |

Машиночитаемые формы:

| Ресурс | Назначение |
| --- | --- |
| `llms-full.txt` | весь корпус документации одним файлом |
| страницы с `.md` | тот же адрес страницы плюс `.md` отдаёт markdown |

Скрипты кита:

| Файл | Назначение |
| --- | --- |
| `templates/net-core.kts` | блок сети, вставляется в каждый скрипт |
| `templates/example-get.kts` | GET по таймеру |
| `templates/example-post.kts` | POST с JSON |
| `templates/example-ai-chat.kts` | Gemini |
| `templates/example-telegram.kts` | Telegram |
| `bridge/nursultan_bridge.py` | мост |
| `bridge/bridge.json` | конфиг |
| `doctor.ps1` | проверка установки |
| `build.ps1` | сборка exe |

Оригинальный API: [docs.nursultan.fun](https://docs.nursultan.fun/).

[PreviousРешение проблем](troubleshooting.md)
