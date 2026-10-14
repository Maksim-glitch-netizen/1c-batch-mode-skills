# Windows

**Фактические тесты выполнены только на Windows. Варианты macOS и Linux на своих ОС не тестировались.**

Основной установщик: `install.ps1`. Альтернативный: `python -B install.py`.
Нужны Python 3.10+, PowerShell 5.1 или 7; Git нужен для полного набора тестов.

```powershell
.\install.ps1 -Client Both -Scope Project -ProjectPath 'C:\work\my-project'
python -B .\install.py --client both --scope project --project-path 'C:\work\my-project' --dry-run
.\scripts\validate.ps1
python -B .\scripts\validate.py
```

Для выполнения пакетных команд нужен отдельный установленный Designer 8.3.27. Новый живой цикл
1С при подготовке этого выпуска не запускался. Историческое свидетельство и текущие проверки
разделены в [validation.md](../validation.md).
