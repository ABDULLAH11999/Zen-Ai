$wshell = New-Object -ComObject WScript.Shell
$proc = Get-Process -Name "fdm" -ErrorAction SilentlyContinue
if ($proc) {
    foreach ($p in $proc) {
        Write-Host "Trying AppActivate on PID $($p.Id)..."
        $res = $wshell.AppActivate($p.Id)
        Write-Host "PID $($p.Id) AppActivate: $res"
        if ($res) {
            Start-Sleep -Milliseconds 300
            $wshell.SendKeys("{ENTER}")
            Write-Host "Sent ENTER to PID $($p.Id)"
        }
    }
} else {
    Write-Host "No fdm process found."
}
