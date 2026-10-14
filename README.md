# 1C Agent Skills

Два связанных skill для Codex и Claude Code: пакетный Конфигуратор 1С 8.3.27 и регистрация
нового корневого объекта через отдельный donor.cf. Лицензия [MIT](LICENSE).

**Фактические тесты выполнены только на Windows. Варианты macOS и Linux подготовлены, но на этих ОС не тестировались.**

Reusable Agent Skills for Codex and Claude Code. Actual tests were performed ONLY on Windows.
macOS and Linux variants are prepared but have NOT been tested on their target OS.
Python 3.10+ and 1C:Enterprise 8.3.27 are required; PowerShell is used by the Windows variant. Documentation is in Russian. The five external scaffolding skills are
installed separately; see [dependencies](docs/dependencies.md).

| Skill | Назначение | Зависимости |
|---|---|---|
| [1c-configurator-batch-8-3-27](skills/1c-configurator-batch-8-3-27/SKILL.md) | Формирование и выполнение документированных пакетных команд Designer | PowerShell либо Python-инструменты; 1С 8.3.27 для выполнения команд |
| [1c-add-new-object](skills/1c-add-new-object/SKILL.md) | Регистрация одного нового корневого объекта через donor.cf и MergeCfg | Пакетный skill, Python, пять внешних skills |

`1c-add-new-object` использует пакетный skill. Пакетный skill работает и самостоятельно.
Python-скрипт первого skill не запускает 1С: порядок действий и вызовы других инструментов
координирует агент. Объект должен быть явно задан типом и именем.

## Варианты ОС

| Вариант | Установщик | Статус |
|---|---|---|
| [Windows](docs/platforms/windows.md) | install.ps1 либо install.py | Фактически тестировался на Windows |
| [macOS](docs/platforms/macos.md) | install-macos.sh / install.py | Подготовлен, на macOS не тестировался |
| [Linux](docs/platforms/linux.md) | install-linux.sh / install.py | Подготовлен, на Linux не тестировался |

Единое ядро skills, отдельные установщики и инструкции ОС. Варианты поставляются отдельными
архивами: windows.zip, macos.tar.gz и linux.tar.gz. Все содержат полный репозиторий без .git.
Наличие архива для ОС не означает прохождение тестов на ней. В каждом архиве
`distribution-profile.json` задаёт целевую ОС, и установщик отклоняет запуск из чужого варианта.
В Git-репозитории профиль universal; ядро обоих skills общее.

## Установка на macOS и Linux

```bash
# macOS
bash ./install-macos.sh --client both --scope user
# Linux
bash ./install-linux.sh --client both --scope user
# Универсальный Python-вариант, включая предварительный просмотр:
python3 -B ./install.py --client both --scope project --project-path '/path/to/project' --dry-run
```

На этих ОС для установки, поиска и проверки skills достаточно Python; PowerShell не обязателен.
Python-варианты внешних scaffold-skills устанавливаются отдельно. Совместимость полного цикла
1С, внешних зависимостей и окружения macOS/Linux требует проверки на целевой системе.

## Установка на Windows

Скачай или клонируй этот репозиторий и открой PowerShell в его корне.
Установщик копирует оба skill; 1С, Python и внешние зависимости он не устанавливает.

```powershell
# Для текущего пользователя Codex
.\install.ps1 -Client Codex -Scope User

# Для текущего пользователя Claude Code
.\install.ps1 -Client Claude -Scope User

# Для обоих клиентов внутри существующего рабочего проекта
.\install.ps1 -Client Both -Scope Project -ProjectPath 'C:\work\my-project'

# Предварительный просмотр без записи файлов
.\install.ps1 -Client Both -Scope Project -ProjectPath 'C:\work\my-project' -WhatIf
```

Если политика PowerShell блокирует скрипт, используй для доверенной локальной копии
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\install.ps1` с теми же аргументами.
Установщик сначала проверяет пакет и все назначения. Существующий skill с отличающимся содержимым
останавливает установку до записи; одинаковая установленная копия пропускается. Автоматической
перезаписи и удаления нет. Для обновления сохрани свои изменения и явно выбери другой каталог
или самостоятельно разреши конфликт.

| Клиент | Для пользователя | Для проекта |
|---|---|---|
| Codex | `~/.agents/skills/` | `<project>/.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `<project>/.claude/skills/` |

Ручная установка: скопируй целиком обе папки из `skills/` в каталог нужного клиента.
Сохраняй их имена и соседнее расположение. После установки проверь каталог навыков клиента;
если изменение не видно, перезапусти сессию. Не устанавливай вторую копию того же skill без нужды.

## Использование

Примеры запросов после установки и настройки внешних зависимостей:

```text
Codex: $1c-configurator-batch-8-3-27 Сформируй команду полной XML-выгрузки моей файловой базы.
Claude Code: /1c-configurator-batch-8-3-27 Сформируй команду полной XML-выгрузки моей файловой базы.

Codex: $1c-add-new-object Подготовь регистрацию Report.Demo_Report в моей тестовой базе.
Claude Code: /1c-add-new-object Подготовь регистрацию Report.Demo_Report в моей тестовой базе.
```

До изменяющей операции агенту нужны явные параметры целевой базы и разрешение на эту задачу.
Задай путь к исполняемому файлу Designer для своей ОС, `/F` или `/S`, аутентификацию, каталог свежей выгрузки и отдельную папку
задачи. Параметры не считываются из корпоративного AGENTS.md и не подставляются по умолчанию.
Все `<...>` в инструкциях - заполнители, не готовые аргументы команды.

## Ограничения

- Тестовая среда этого выпуска: только Windows, PowerShell 5.1/7, Python. Подготовлены варианты
  macOS и Linux на Python 3.10+; на своих ОС они не тестировались. Граница версии 1С: 8.3.27.
- Перед работой с базой обязателен свежий baseline. Если проект использует хранилище, соблюдай его
  синхронизацию, захват и помещение. Настройки хранилища и учётные данные не входят в пакет.
- Не запускай параллельные пакетные Designer для одной базы. Межагентной блокировки здесь нет.
- Регистрация каркаса и обновление конфигурации БД - отдельные этапы. Сначала контрольная XML-выгрузка,
  затем разработка реального объекта, валидация и только после этого UpdateDBCfg.
- Поддержка типа в Python означает знание имени и каталога XML. Типы с обязательными внешними
  зависимостями требуют отдельного проверенного donor-сценария.
- `verify-main` проверяет состав корневых объектов; неизменность содержимого существующих объектов
  и бизнес-логика проверяются отдельно.

## Проверка и сопровождение

```powershell
# Фактические проверки этого выпуска выполнялись только на Windows.
.\scripts\validate.ps1
# После осознанного изменения файлов обновить контрольные суммы:
python -B .\scripts\update-manifests.py --write
.\scripts\validate.ps1
```

Для Python-проверки используй `python3 -B scripts/validate.py`; для полного Windows-набора
нужны Python, PowerShell и Git. Python-команда также фактически проверялась только на Windows. Проверки работают без установленной 1С и не подключаются к базам. Они проверяют структуру,
контрольные суммы, синтаксис PowerShell, Python-тесты и установку в изолированные каталоги.
[Границы проверки](docs/validation.md), [внешние зависимости](docs/dependencies.md),
[подготовка публикации](docs/publishing.md), [сторонние материалы](THIRD_PARTY.md).

Правила обнаружения: [официальная документация OpenAI](https://learn.chatgpt.com/docs/build-skills)
и [документация Claude Code](https://code.claude.com/docs/en/skills).
## Сообщить об ошибке

Открой раздел **Issues → New issue** в GitHub и выбери форму **Ошибка / Bug report**.
Укажи навык, версию комплекта, ОС, клиент и шаги воспроизведения. Для вопросов и предложений
можно создать обычный issue. Не прикладывай пароли, токены, реальные базы и бизнес-данные.

Reports and suggestions are welcome in **Issues**. Include the skill, bundle version, OS,
client and reproduction steps. Actual release tests were performed only on Windows;
macOS/Linux reports should include the environment details.
