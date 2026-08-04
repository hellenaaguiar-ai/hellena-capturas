# Cria os atalhos (.lnk) de Ideia/Reuniao/Terapia na Area de Trabalho, ja
# com icone proprio (assets/icons/*.ico) em vez do icone generico de .bat.
#
# Uso: abra o PowerShell dentro da pasta do projeto e rode:
#   .\scripts\windows\criar-atalhos-desktop.ps1
#
# Rodar de novo a qualquer momento recria os atalhos (por exemplo, se voce
# mudou o caminho do projeto).

$ErrorActionPreference = "Stop"

$projectDir = (Resolve-Path "$PSScriptRoot\..\..\").Path.TrimEnd('\')
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell

$modes = @(
    @{ Nome = "Gravar Ideia";   Bat = "Gravar Ideia.bat";   Icone = "ideia.ico" },
    @{ Nome = "Gravar Reuniao"; Bat = "Gravar Reuniao.bat"; Icone = "reuniao.ico" },
    @{ Nome = "Gravar Terapia"; Bat = "Gravar Terapia.bat"; Icone = "terapia.ico" }
)

foreach ($modo in $modes) {
    $batPath = Join-Path $projectDir "scripts\windows\$($modo.Bat)"
    $iconPath = Join-Path $projectDir "assets\icons\$($modo.Icone)"
    $lnkPath = Join-Path $desktop "$($modo.Nome).lnk"

    if (-not (Test-Path $batPath)) {
        Write-Warning "Nao encontrei $batPath - pulando."
        continue
    }

    $shortcut = $shell.CreateShortcut($lnkPath)
    $shortcut.TargetPath = $batPath
    $shortcut.WorkingDirectory = $projectDir
    $shortcut.IconLocation = $iconPath
    $shortcut.WindowStyle = 7  # minimizado
    $shortcut.Save()

    Write-Host "Criado: $lnkPath"
}

Write-Host "`nPronto. Os 3 atalhos estao na Area de Trabalho, com icone proprio."
