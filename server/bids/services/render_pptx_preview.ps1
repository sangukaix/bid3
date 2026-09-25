param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$SourcePath = (Resolve-Path -LiteralPath $SourcePath).Path
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$powerPoint = New-Object -ComObject PowerPoint.Application
$presentation = $null

try {
    $presentation = $powerPoint.Presentations.Open(
        $SourcePath,
        $true,
        $true,
        $false
    )
    $presentation.SaveAs($OutputPath, 32)
}
finally {
    try {
        if ($null -ne $presentation) { $presentation.Close() }
    }
    finally {
        # Never close a presentation the user has open in PowerPoint.
        if ($powerPoint.Presentations.Count -eq 0) { $powerPoint.Quit() }
    }
}
