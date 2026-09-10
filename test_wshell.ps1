$wshell = New-Object -ComObject WScript.Shell
$targets = @("Free Download Manager", "Download", "FDM", "Detroit", "FitGirl")
foreach ($t in $targets) {
    $res = $wshell.AppActivate($t)
    Write-Host "AppActivate('$t') result: $res"
    if ($res) {
        Start-Sleep -Milliseconds 300
        $wshell.SendKeys("{ENTER}")
        Write-Host "Sent ENTER to $t"
    }
}
