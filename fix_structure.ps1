# fix_structure.ps1
Write-Host "Fixing project structure..." -ForegroundColor Cyan

# Create all necessary folders
$folders = @(
    "app\bot\handlers",
    "app\db\models",
    "app\db\repositories",
    "migrations\versions",
    "tests"
)

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    Write-Host "Created folder: $folder" -ForegroundColor Green
}

# Remove incorrect folders if they exist
$badFolders = @("app\handlers", "app\models", "app\repositories", "app\migrations")
foreach ($folder in $badFolders) {
    if (Test-Path $folder) {
        Remove-Item -Path $folder -Recurse -Force
        Write-Host "Removed folder: $folder" -ForegroundColor Yellow
    }
}

# Create __init__.py files
$initFiles = @(
    "app\bot\handlers\__init__.py",
    "app\db\models\__init__.py",
    "app\db\repositories\__init__.py",
    "tests\__init__.py"
)

foreach ($file in $initFiles) {
    New-Item -ItemType File -Path $file -Force | Out-Null
    Write-Host "Created file: $file" -ForegroundColor Green
}

# Create main project files (empty)
$projectFiles = @(
    "app\config.py",
    "app\main.py",
    "app\bot\middlewares.py",
    "app\bot\keyboards.py",
    "app\db\database.py",
    "app\db\base.py",
    "app\utils\logging.py",
    "app\api\server.py",
    "run.py",
    "alembic.ini",
    "migrations\env.py",
    "tests\conftest.py",
    "tests\test_users.py"
)

foreach ($file in $projectFiles) {
    if (-not (Test-Path $file)) {
        New-Item -ItemType File -Path $file -Force | Out-Null
        Write-Host "Created file: $file" -ForegroundColor Green
    }
}

Write-Host "`nStructure fixed successfully!" -ForegroundColor Yellow
Write-Host "Now fill the files with code." -ForegroundColor Cyan