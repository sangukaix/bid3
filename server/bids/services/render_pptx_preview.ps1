param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$powerPoint = New-Object -ComObject PowerPoint.Application

try {
    $presentation = $powerPoint.Presentations.Open(
        $SourcePath,
        $true,
        $true,
        $false
    )
    $presentation.SaveAs($OutputPath, 32)
    $presentation.Close()
}
finally {
    $powerPoint.Quit()
}
