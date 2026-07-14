param(
    [string]$Root = (Get-Location).Path,
    [string]$OutputFolder = "옵시디언 변환본"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression.FileSystem

$rootPath = [IO.Path]::GetFullPath($Root)
$outputRoot = Join-Path $rootPath $OutputFolder
$scriptPath = [IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Read-ZipEntryText {
    param([string]$Path, [string]$EntryName)
    $zip = [IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $entry = $zip.Entries | Where-Object { $_.FullName -eq $EntryName } | Select-Object -First 1
        if (-not $entry) { return $null }
        $reader = New-Object IO.StreamReader($entry.Open(), [Text.Encoding]::UTF8)
        try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $zip.Dispose() }
}

function Get-ZipEntryNames {
    param([string]$Path, [string]$Pattern)
    $zip = [IO.Compression.ZipFile]::OpenRead($Path)
    try {
        return @($zip.Entries | Where-Object { $_.FullName -match $Pattern } | ForEach-Object FullName)
    } finally { $zip.Dispose() }
}

function Convert-XmlText {
    param([string]$XmlText, [string[]]$ParagraphNames = @('p'))
    if ([string]::IsNullOrWhiteSpace($XmlText)) { return "" }
    $doc = New-Object Xml.XmlDocument
    $doc.PreserveWhitespace = $false
    $doc.LoadXml($XmlText)
    $lines = New-Object Collections.Generic.List[string]
    $nodes = $doc.SelectNodes("//*") | Where-Object { $ParagraphNames -contains $_.LocalName }
    foreach ($node in $nodes) {
        $parts = @($node.SelectNodes(".//*[local-name()='t']") | ForEach-Object { $_.InnerText })
        if ($parts.Count -eq 0 -and $node.LocalName -eq 'p') {
            $parts = @($node.SelectNodes(".//*[local-name()='text']") | ForEach-Object { $_.InnerText })
        }
        $line = (($parts -join '') -replace '\s+', ' ').Trim()
        if ($line) { $lines.Add($line) }
    }
    return ($lines -join "`r`n`r`n")
}

function Convert-Docx {
    param([string]$Path)
    $xml = Read-ZipEntryText $Path 'word/document.xml'
    return Convert-XmlText $xml @('p')
}

function Convert-Hwpx {
    param([string]$Path)
    $names = Get-ZipEntryNames $Path '^Contents/section[0-9]+\.xml$'
    $ordered = $names | Sort-Object { [int]([regex]::Match($_, '[0-9]+').Value) }
    $sections = foreach ($name in $ordered) {
        Convert-XmlText (Read-ZipEntryText $Path $name) @('p')
    }
    return (($sections | Where-Object { $_ }) -join "`r`n`r`n---`r`n`r`n")
}

function Convert-Pptx {
    param([string]$Path)
    $names = Get-ZipEntryNames $Path '^ppt/slides/slide[0-9]+\.xml$'
    $ordered = $names | Sort-Object { [int]([regex]::Match($_, 'slide([0-9]+)', 'IgnoreCase').Groups[1].Value) }
    $slides = New-Object Collections.Generic.List[string]
    $number = 0
    foreach ($name in $ordered) {
        $number++
        $xmlText = Read-ZipEntryText $Path $name
        $doc = New-Object Xml.XmlDocument
        $doc.LoadXml($xmlText)
        $texts = @($doc.SelectNodes("//*[local-name()='t']") | ForEach-Object { $_.InnerText.Trim() } | Where-Object { $_ })
        $slides.Add("## 슬라이드 $number`r`n`r`n" + ($texts -join "  `r`n"))
    }
    return ($slides -join "`r`n`r`n")
}

function Get-XlsxSharedStrings {
    param([string]$Path)
    $xmlText = Read-ZipEntryText $Path 'xl/sharedStrings.xml'
    if (-not $xmlText) { return @() }
    $doc = New-Object Xml.XmlDocument
    $doc.LoadXml($xmlText)
    return @($doc.SelectNodes("//*[local-name()='si']") | ForEach-Object {
        (@($_.SelectNodes(".//*[local-name()='t']") | ForEach-Object InnerText) -join '')
    })
}

function Convert-Xlsx {
    param([string]$Path)
    $shared = @(Get-XlsxSharedStrings $Path)
    $names = Get-ZipEntryNames $Path '^xl/worksheets/sheet[0-9]+\.xml$'
    $ordered = $names | Sort-Object { [int]([regex]::Match($_, '[0-9]+').Value) }
    $sheets = New-Object Collections.Generic.List[string]
    $sheetNo = 0
    foreach ($name in $ordered) {
        $sheetNo++
        $doc = New-Object Xml.XmlDocument
        $doc.LoadXml((Read-ZipEntryText $Path $name))
        $rows = New-Object Collections.Generic.List[string]
        foreach ($row in $doc.SelectNodes("//*[local-name()='row']")) {
            $cells = New-Object Collections.Generic.List[string]
            foreach ($cell in $row.SelectNodes("./*[local-name()='c']")) {
                $ref = $cell.GetAttribute('r')
                $type = $cell.GetAttribute('t')
                $v = $cell.SelectSingleNode("./*[local-name()='v']")
                $value = if ($v) { $v.InnerText } else { '' }
                if ($type -eq 's' -and $value -match '^\d+$' -and [int]$value -lt $shared.Count) { $value = $shared[[int]$value] }
                $cells.Add("$ref: $value")
            }
            if ($cells.Count) { $rows.Add('- ' + ($cells -join ' | ')) }
        }
        $sheets.Add("## 시트 $sheetNo`r`n`r`n" + ($rows -join "`r`n"))
    }
    return ($sheets -join "`r`n`r`n")
}

function Get-RelativeVaultPath {
    param([string]$Path)
    return [IO.Path]::GetRelativePath($rootPath, $Path).Replace('\', '/')
}

function Write-Markdown {
    param([IO.FileInfo]$Source, [string]$Body, [string]$Status = '변환완료')
    $relative = [IO.Path]::GetRelativePath($rootPath, $Source.FullName)
    $relativeDir = Split-Path $relative -Parent
    $targetDir = if ($relativeDir) { Join-Path $outputRoot $relativeDir } else { $outputRoot }
    [IO.Directory]::CreateDirectory($targetDir) | Out-Null
    $target = Join-Path $targetDir ($Source.BaseName + '.md')
    $sourceLink = Get-RelativeVaultPath $Source.FullName
    $safeTitle = $Source.BaseName.Replace('"', "'")
    $content = @"
---
title: "$safeTitle"
type: converted-document
status: $Status
source_format: $($Source.Extension.TrimStart('.').ToLowerInvariant())
source: "$sourceLink"
converted: 2026-07-13
tags: [문서변환, 인박스, 옵시디언]
---

# $($Source.BaseName)

> [!info] 원본
> [[$sourceLink|원본 파일 열기]]  
> 복잡한 표·도형·서식은 단순화될 수 있으므로 중요한 수치와 서명은 원본을 함께 확인하세요.

$Body
"@
    [IO.File]::WriteAllText($target, $content.TrimEnd() + "`r`n", $utf8)
    return $target
}

[IO.Directory]::CreateDirectory($outputRoot) | Out-Null
$files = @(Get-ChildItem -LiteralPath $rootPath -Recurse -File | Where-Object {
    -not $_.FullName.StartsWith($outputRoot, [StringComparison]::OrdinalIgnoreCase) -and
    $_.FullName -ne $scriptPath -and
    $_.Name -notlike '.stale-*' -and $_.Name -notlike '.truncated-*'
})

$results = New-Object Collections.Generic.List[object]
$hwpApp = $null
try {
    foreach ($file in $files) {
        $ext = $file.Extension.ToLowerInvariant()
        $body = $null
        $status = '원본연결'
        try {
            switch ($ext) {
                '.docx' { $body = Convert-Docx $file.FullName; $status = '변환완료' }
                '.hwpx' { $body = Convert-Hwpx $file.FullName; $status = '변환완료' }
                '.pptx' { $body = Convert-Pptx $file.FullName; $status = '변환완료' }
                '.xlsx' { $body = Convert-Xlsx $file.FullName; $status = '변환완료' }
                '.hwp' {
                    if (-not $hwpApp) {
                        $hwpApp = New-Object -ComObject HwpFrame.HwpObject
                        try { $hwpApp.XHwpWindows.Item(0).Visible = $false } catch {}
                    }
                    $temp = Join-Path $env:TEMP ([guid]::NewGuid().ToString() + '.txt')
                    $opened = $hwpApp.Open($file.FullName, 'HWP', 'forceopen:true')
                    if (-not $opened) { throw '한컴오피스에서 문서를 열지 못했습니다.' }
                    $saved = $hwpApp.SaveAs($temp, 'TEXT', '')
                    if (-not $saved -or -not (Test-Path -LiteralPath $temp)) { throw '텍스트 저장에 실패했습니다.' }
                    $body = [IO.File]::ReadAllText($temp, [Text.Encoding]::Default)
                    Remove-Item -LiteralPath $temp -Force
                    $hwpApp.Clear(1)
                    $status = '변환완료'
                }
            }
            if ($null -ne $body) {
                if ([string]::IsNullOrWhiteSpace($body)) { $body = '_추출된 텍스트가 없습니다. 이미지형 문서일 수 있으니 원본을 확인하세요._'; $status = '확인필요' }
                $target = Write-Markdown $file $body $status
                $results.Add([pscustomobject]@{ Source=$file; Status=$status; Target=$target; Error='' })
            } else {
                $results.Add([pscustomobject]@{ Source=$file; Status=$status; Target=''; Error='' })
            }
        } catch {
            try { if ($hwpApp -and $ext -eq '.hwp') { $hwpApp.Clear(1) } } catch {}
            $results.Add([pscustomobject]@{ Source=$file; Status='변환실패'; Target=''; Error=$_.Exception.Message })
        }
    }
} finally {
    if ($hwpApp) {
        try { $hwpApp.Quit() } catch {}
        try { [Runtime.InteropServices.Marshal]::FinalReleaseComObject($hwpApp) | Out-Null } catch {}
    }
}

$indexLines = New-Object Collections.Generic.List[string]
$indexLines.Add('---')
$indexLines.Add('title: "인박스 자료 인덱스"')
$indexLines.Add('type: index')
$indexLines.Add('status: active')
$indexLines.Add('updated: 2026-07-13')
$indexLines.Add('tags: [문서변환, 인박스, 옵시디언]')
$indexLines.Add('---')
$indexLines.Add('')
$indexLines.Add('# 인박스 자료 인덱스')
$indexLines.Add('')
$indexLines.Add('원본은 그대로 보존했습니다. 변환 문서는 제목을 누르면 열립니다.')
$indexLines.Add('')

$grouped = $results | Group-Object { $dir = Split-Path ([IO.Path]::GetRelativePath($rootPath, $_.Source.FullName)) -Parent; if ($dir) { $dir } else { '인박스 루트' } } | Sort-Object Name
foreach ($group in $grouped) {
    $indexLines.Add("## $($group.Name)")
    $indexLines.Add('')
    foreach ($item in ($group.Group | Sort-Object { $_.Source.Name })) {
        $src = Get-RelativeVaultPath $item.Source.FullName
        if ($item.Target) {
            $targetRel = Get-RelativeVaultPath $item.Target
            $indexLines.Add("- [[$targetRel|$($item.Source.BaseName)]] — $($item.Status) · [원본]($src)")
        } elseif ($item.Status -eq '변환실패') {
            $indexLines.Add("- **$($item.Source.Name)** — 변환 실패: $($item.Error) · [원본]($src)")
        } elseif (@('.pdf','.png','.jpg','.jpeg','.gif','.webp','.m4a','.mp3','.wav','.mp4','.webm','.md') -contains $item.Source.Extension.ToLowerInvariant()) {
            $indexLines.Add("- [[$src|$($item.Source.Name)]] — 옵시디언에서 원본 열기")
        } else {
            $indexLines.Add("- [[$src|$($item.Source.Name)]] — 원본 연결")
        }
    }
    $indexLines.Add('')
}

$summary = $results | Group-Object Status | Sort-Object Name
$indexLines.Add('## 변환 결과')
$indexLines.Add('')
foreach ($s in $summary) { $indexLines.Add("- $($s.Name): $($s.Count)개") }
[IO.File]::WriteAllLines((Join-Path $outputRoot '00 인박스 자료 인덱스.md'), $indexLines, $utf8)

$results | Group-Object Status | Sort-Object Name | ForEach-Object { "{0}: {1}" -f $_.Name, $_.Count }
