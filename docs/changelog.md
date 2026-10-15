# Журнал изменений

Версии кита. Мост и шаблоны обновляются согласованно: при несовместимой смене протокола поднимается `proto` в bridge.json.

## 0.1.0 — 2026-10-15

Первая версия. Протокол `proto 1`, мост, шаблоны, документация.

| Компонент | Что вошло |
| --- | --- |
| `bridge/nursultan_bridge.py` | опрос через MCP, конверт `NETREQ`/`NETRESP`, GET/POST/PUT/PATCH/DELETE/HEAD, jsonpath, `{{KEY}}`, allowlist, блокировка приватных сетей, атомарная запись, дедупликация, очистка файлов |
| `bridge/bridge.json` | конфиг: `mcpLink`, `pollMs`, `allowlist`, `allowPrivate`, лимиты, `secrets` |
| `templates/net-core.kts` | блок `internet-core`: `netSend`, `netGet`, `netPost`, `netTick`, `netBusy`, `netJsonEscape` |
| `templates/example-*.kts` | примеры: GET по таймеру, POST с JSON, Gemini, Telegram |
| `doctor.ps1` | проверка установки: конфиг, MCP, запись в assets |
| `build.ps1` | сборка exe через PyInstaller |
| документация | 12 страниц, `llms-full.txt` для нейросетей, `sitemap.xml` |

## Совместимость

| Элемент | Правило |
| --- | --- |
| `proto: 1` | текущая версия конверта; мост предупреждает в логе о несовпадении |
| `requireApi(2)` | минимальный API скриптов клиента |
| `internet-core` | вставляется целиком, правки только между маркерами |
| обновление | заменить мост (или exe), сохранить bridge.json; шаблоны скопировать заново |

## Что планируется

| Идея | Статус |
| --- | --- |
| повторные попытки в самом мосте (retry с backoff) | обсуждается |
| директива `useragent:` в конверте | обсуждается |
| больше рецептов API | пополняется по мере вопросов |

[Вопросы и ответы](faq.md) · [Карта сайта](sitemap.md)
