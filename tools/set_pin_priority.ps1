# Sets Windows Hello PIN as the 1st Priority Credential Provider
$pinGuid = "{D6886603-9D2F-4EB2-B667-1971041FA96B}"
$regPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System"

if (!(Test-Path $regPath)) {
    New-Item -Path $regPath -Force | Out-Null
}

Set-ItemProperty -Path $regPath -Name "DefaultCredentialProvider" -Value $pinGuid -Force
Write-Host "SUCCESS: PIN configured as 1st Priority Default Credential Provider!"
