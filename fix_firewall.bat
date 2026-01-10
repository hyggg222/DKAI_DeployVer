@echo off
echo Adding Firewall Rule for DK AI Server (Port 8001)...
netsh advfirewall firewall delete rule name="DKAI_Allow_8001"
netsh advfirewall firewall add rule name="DKAI_Allow_8001" dir=in action=allow protocol=TCP localport=8001 profile=any
echo Done.
pause
