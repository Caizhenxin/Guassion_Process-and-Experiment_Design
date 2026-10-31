# 总台同步补丁（P0-1 / P0-2）
# 为什么要你手动跑：本会话的沙箱只能写 GP 项目目录，D:\GitHub_programe\GitHub\DSH_Workbench 是只读的。
# 用法：
#   1) 先看会改什么      powershell -NoProfile -ExecutionPolicy Bypass -File _交接\_tools\总台同步.ps1
#   2) 确认后真写        powershell -NoProfile -ExecutionPolicy Bypass -File _交接\_tools\总台同步.ps1 -Apply
# 特性：幂等（已改过就跳过）、每步都回读校验（不做「幽灵成功」）、失败退出码 1。

param([switch]$Apply)

$ErrorActionPreference = "Stop"
$GP      = "D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
$WB      = "D:\GitHub_programe\GitHub\DSH_Workbench"
$Report  = Join-Path $GP "6_Workbench\审计-与淋雨家工作台差距-20261030.md"
$Dst     = Join-Path $WB "docs\审计-与淋雨家工作台差距-20261030.md"
$Idx     = Join-Path $WB "index\总索引.md"
$enc     = New-Object System.Text.UTF8Encoding($false)
$fail    = 0
function Step($name) { Write-Output ""; Write-Output ("[{0}] {1}" -f $(if ($Apply) { "写" } else { "试" }), $name) }
function Ok($msg)    { Write-Output ("  ✓ {0}" -f $msg) }
function Bad($msg)   { Write-Output ("  ✗ {0}" -f $msg); $script:fail++ }

# ── P0-1：审计报告归 docs/ ─────────────────────────────────────────────
Step "P0-1 审计报告 → 总台 docs/"
if (-not (Test-Path $Report)) { Bad "源文件不在：$Report" }
else {
  $srcHash = (Get-FileHash $Report -Algorithm SHA256).Hash
  if ((Test-Path $Dst) -and ((Get-FileHash $Dst -Algorithm SHA256).Hash -eq $srcHash)) { Ok "已是最新，跳过" }
  elseif (-not $Apply) { Ok ("将复制 {0:N1} KB → docs\" -f ((Get-Item $Report).Length / 1KB)) }
  else {
    Copy-Item $Report $Dst -Force
    if ((Get-FileHash $Dst -Algorithm SHA256).Hash -eq $srcHash) { Ok "已复制并校验哈希一致" } else { Bad "复制后哈希不一致" }
  }
}

# ── P0-2：总索引里「插件已搁置」与进度矛盾 ─────────────────────────────
Step "P0-2 总索引：插件从「留档·搁置」改成「活」"
$lines = @(Get-Content $Idx -Encoding UTF8)
$oldRow = $lines | Where-Object { $_ -match '试行版插件' -and $_ -match '搁置' }
if (-not $oldRow) { Ok "已无「搁置」条目，跳过" }
elseif (-not $Apply) { Ok ("将删除：{0}" -f $oldRow.Trim()) ; Ok "并在「活」表插入插件行 + 纪律行" }
else {
  $anchor = -1
  for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match '^\|\s*参考对照清单') { $anchor = $i; break } }
  if ($anchor -lt 0) { Bad "找不到「参考对照清单」锚点，未改动" }
  else {
    $ins = @(
      '| 试行版插件「我的工作台」 | `D:\GitHub_programe\GitHub\dsh-my-project-workbench` | 两条腿之一：P5 已完成、M4 未开工（2026-10-30 核实，不再是「搁置」） |',
      '| GP 项目纪律 | `<GP root>/_交接/工作台纪律.md` | 宪法 v1：只认机主 / 修改权分层 / 派单与回执 / 记忆三层 |',
      '| GP 差距审计 | `docs/审计-与淋雨家工作台差距-20261030.md` | 五问结论 + 补齐清单，2026-10-30 |'
    )
    $kept = @($lines | Where-Object { -not ($_ -match '试行版插件' -and $_ -match '搁置') })
    $out = @()
    for ($i = 0; $i -lt $kept.Count; $i++) {
      $out += $kept[$i]
      if ($kept[$i] -match '^\|\s*参考对照清单') { $out += $ins }
    }
    [System.IO.File]::WriteAllLines($Idx, $out, $enc)
    $check = [System.IO.File]::ReadAllText($Idx, $enc)
    if ($check -match '机主搁置') { Bad "回读仍有「机主搁置」" }
    elseif ($check -notmatch '两条腿之一') { Bad "回读没找到新插件行" }
    elseif ($check -notmatch '工作台纪律') { Bad "回读没找到纪律行" }
    else { Ok "已改并回读校验：插入 3 行、删 1 行" }
  }
}

Write-Output ""
if ($fail -gt 0) { Write-Output ("有 {0} 步失败，请把上面的 ✗ 发给我。" -f $fail); exit 1 }
if ($Apply) { Write-Output "完成。建议再跑一次（应全部显示「跳过」）确认幂等。" }
else { Write-Output "以上是试运行。确认无误后加 -Apply 真写。" }
