@echo off
echo 正在尝试添加防火墙规则，开放端口 8000...
netsh advfirewall firewall add rule name="FindIt Backend" dir=in action=allow protocol=TCP localport=8000
if %errorlevel% equ 0 (
    echo 成功！端口 8000 已开放。
) else (
    echo.
    echo 失败：请右键点击此文件，选择【以管理员身份运行】。
)
pause
