# Карта сайта

| Страница | Файл | Содержание |
| --- | --- | --- |
| Что это | [index.md](index.md) | состав, схема, ограничения, быстрый старт |
| Установка | [install.md](install.md) | MCP, bridge.json, запуск, сборка exe, автозапуск |
| Протокол | [protocol.md](protocol.md) | конверт запроса и ответа, jsonpath, ключи, проверки |
| API скрипта | [api.md](api.md) | функции `internet-core`, шаблон обработчика, таймауты |
| Примеры | [examples.md](examples.md) | погода, POST, Gemini, Telegram, вебхуки |
| Внутреннее устройство | [architecture.md](architecture.md) | цикл моста, разбор конверта, jsonpath, атомарная запись, расширение |
| Безопасность | [security.md](security.md) | модель угроз, allowlist, приватные сети, секреты, чек-лист |
| Правила для ИИ | [ai-rules.md](ai-rules.md) | инструкция для нейронки, запреты, чек-лист |
| Рецепты API | [recipes.md](recipes.md) | каталог форм запросов: параметры, ключи, повторы, rate limit |
| Решение проблем | [troubleshooting.md](troubleshooting.md) | симптом → причина → действие |
| Вопросы и ответы | [faq.md](faq.md) | частые вопросы по киту и песочнице |
| Журнал изменений | [changelog.md](changelog.md) | версии кита и совместимость |

Машиночитаемые формы:

| Ресурс | Назначение |
| --- | --- |
| `llms-full.txt` | весь корпус документации одним файлом |
| `sitemap.xml` | карта URL всех страниц, генерируется при сборке |

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
