# Nursultan Internet Kit

Официальный мост интернета для скриптов [Nursultan](https://nursultan.fun/): скрипты получают HTTPS через отдельный процесс, песочница клиента не нарушается.

Документация: `docs/` (MkDocs Material). Быстрый старт — [docs/install.md](docs/install.md).

## Структура

```
nursultan-internet-kit/
├── bridge/
│   ├── nursultan_bridge.py      мост, только stdlib Python
│   ├── bridge.example.json      шаблон конфига
│   └── bridge.json              твой конфиг с секретами, в git не попадает
├── templates/
│   ├── net-core.kts             блок сети для вставки в скрипт
│   ├── example-get.kts          погода, GET по таймеру
│   ├── example-post.kts         POST с JSON
│   ├── example-ai-chat.kts      Gemini
│   └── example-telegram.kts     Telegram
├── docs/                        исходники сайта
├── tools/make_llms.py           сборка llms-full.txt
├── mkdocs.yml                   конфиг сайта
├── doctor.ps1                   проверка установки
├── build.ps1                    сборка exe
└── .github/workflows/deploy.yml публикация сайта
```

## Разработка

```
pip install mkdocs-material
python bridge/nursultan_bridge.py --selftest
python tools/make_llms.py
mkdocs serve
```

Сайт: `mkdocs serve` → http://127.0.0.1:8000.

## Публикация

1. Заменить `USERNAME` в `mkdocs.yml` на свой GitHub-логин.
2. Создать репозиторий `nursultan-internet-kit`, запушить.
3. Settings → Pages → Source: GitHub Actions.
4. Каждый push в `main` собирает сайт и `llms-full.txt` и публикует на Pages.

## Релиз кита

`build.ps1` собирает `dist/nursultan-internet-bridge.exe`. В архив для пользователей кладутся: exe, `bridge.json`, `templates/`, `docs/`, `doctor.ps1`.

## Правила

- протокол версионируется через `proto`; несовместимые изменения — новый номер;
- блок `internet-core` и мост обновляются парно;
- секреты живут только в `bridge.json`, в скриптах — только `keyref`;
- каждый запрос попадает в `requests.log`.
