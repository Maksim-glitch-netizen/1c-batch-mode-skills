# Границы проверки

**Фактические тесты выполнены только на Windows. Варианты macOS и Linux подготовлены, но на этих ОС не тестировались.**

**All actual tests were run only on Windows. No macOS or Linux native tests were performed.**

## Автоматическая проверка поставки

`scripts/validate.ps1` запускает структурную проверку, оба валидатора skills, анализ PowerShell
через Parser API, Python unit tests и тесты установщика в новых временных каталогах.
Ни одна из этих проверок не запускает Designer и не изменяет информационную базу.
GitHub Actions повторяет их на Windows с PowerShell 5.1 и PowerShell 7; наличие workflow не означает,
что он уже был выполнен на GitHub. Фактические локальные результаты фиксируются в отчёте задачи.

Проверяются в том числе конфликт до копирования, повторная установка, WhatIf, пути с пробелами
и кириллицей, целостность manifest и поиск MergeCfg в справочнике 11. Отдельный тест
проверяет контрольные суммы после Git checkout-index при core.autocrlf=true; .gitattributes
закрепляет LF для текстовых файлов.

## Python-вариант и Unix-оболочки

`scripts/validate.py`, Python-установщик, поиск и Python-валидаторы фактически запускались только
на Windows. Проверка синтаксиса shell-установщиков через Git Bash на Windows, если выполнена,
не является тестом Linux или macOS. Профили ОС и адаптированные шаблоны Designer не подтверждают
живой запуск 1С на этих ОС. CI runs only on windows-latest; run results are available in the repository Actions tab.
Машиночитаемый статус находится в [platforms.json](../platforms.json).

## Историческое свидетельство

В локальных исходниках исходного пакетного skill описан успешный тест от 17.09.2026 на
8.3.27.2214 в двух изолированных файловых базах: LoadConfigFromFiles, DumpCfg, MergeCfg и
контрольный DumpConfigToFiles. Это история исходного рецепта, не новый интеграционный тест
публикационного комплекта и не подтверждение режима поддержки произвольной серверной базы.

Полный цикл на пользовательской 1С и выполнение через установленные Codex/Claude Code должны
проверяться отдельно в тестовой базе. Тесты установки подтверждают расположение и целостность
файлов, а не поведение модели. Справочники сохраняют исторические даты сверки официальных источников.

Python CLI output is UTF-8, including redirected streams. Regression checks force cp1252 for
installation into Cyrillic paths and documentation search. All actual tests remain Windows only.
