# build_context.ps1
# Собирает PROJECT_FULL.md = содержимое _header.md + все ключевые .py-файлы.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$outFile = Join-Path $root "PROJECT_FULL.md"
$headerFile = Join-Path $root "_header.md"

if (-not (Test-Path $headerFile)) {
    Write-Host "Файл _header.md не найден в корне проекта!" -ForegroundColor Red
    exit 1
}

$files = @(
    "app/main.py",
    "app/config.py",
    "app/services/ai_service.py",
    "app/services/access_service.py",
    "app/services/reminder_service.py",
    "app/services/trial_service.py",
    "app/services/payment_service.py",
    "app/services/subscription_service.py",
    "app/services/dynamics_service.py",
    "app/services/dynamics_data_builder.py",
    "app/services/diary_event_service.py",
    "app/services/features.py",
    "app/db/models/user.py",
    "app/db/models/subscription.py",
    "app/db/models/diary_event.py",
    "app/db/models/reminder.py",
    "app/db/models/usage.py",
    "app/db/repositories/reminder.py",
    "app/db/repositories/subscription.py",
    "app/db/repositories/diary_repository.py",
    "app/bot/handlers/describe_state.py",
    "app/bot/handlers/dynamics.py",
    "app/bot/handlers/profile.py",
    "app/bot/handlers/settings.py",
    "app/bot/handlers/reminders.py",
    "app/bot/handlers/pro.py",
    "app/bot/handlers/menu.py",
    "app/bot/handlers/how_it_works.py",
    "app/bot/handlers/diary.py",
    "app/bot/handlers/history.py",
    "app/bot/handlers/survey_launcher.py",
    "app/bot/handlers/__init__.py",
    "app/bot/handlers/surveys/__init__.py",
    "app/bot/states.py",
    "app/bot/keyboards/reminders.py",
    "app/bot/keyboards/dynamics.py"
)

$output = New-Object System.Collections.Generic.List[string]

$headerContent = Get-Content -Path $headerFile -Raw -Encoding UTF8
$output.Add($headerContent)

$added = 0
$skipped = 0

foreach ($file in $files) {
    $fullPath = Join-Path $root $file

    if (-not (Test-Path $fullPath)) {
        Write-Host "[SKIP] Не найден: $file" -ForegroundColor Yellow
        $skipped++
        continue
    }

    $content = Get-Content -Path $fullPath -Raw -Encoding UTF8

    $output.Add("")
    $output.Add("---")
    $output.Add("")
    $output.Add("<details>")
    $output.Add("<summary><b>Файл: " + $file + "</b></summary>")
    $output.Add("")
    $output.Add('```python')
    $output.Add($content)
    $output.Add('```')
    $output.Add("")
    $output.Add("</details>")
    $output.Add("")

    Write-Host "[OK] Добавлен: $file" -ForegroundColor Green
    $added++
}

$output -join "`n" | Out-File -FilePath $outFile -Encoding UTF8

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Готово: $outFile" -ForegroundColor Cyan
Write-Host "Файлов добавлено: $added" -ForegroundColor Cyan
Write-Host "Файлов пропущено: $skipped" -ForegroundColor Cyan

if (Test-Path $outFile) {
    $size = (Get-Item $outFile).Length
    $sizeKB = [math]::Round($size / 1KB, 2)
    Write-Host "Размер: $sizeKB KB" -ForegroundColor Cyan
}
Write-Host "================================================" -ForegroundColor Cyan