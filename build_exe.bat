@echo off
pushd "%~dp0"
echo Building DK_AI Server...
pyinstaller --noconfirm --onedir --console --name "DKAI_Server" ^
    --add-data "src;src" ^
    --add-data "weights;weights" ^
    --hidden-import "engineio.async_drivers.asgi" ^
    --collect-all ultralytics ^
    ai_server.py

echo Build Complete! Output in dist/DKAI_Server
popd
pause
