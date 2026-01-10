@echo off
pushd "%~dp0"
echo Building DK_AI Server FINAL VERSION...
..\venv\Scripts\pyinstaller --noconfirm --onedir --console --name "DKAI_Server_Final" ^
    --add-data "src;src" ^
    --add-data "weights;weights" ^
    --add-data "templates;templates" ^
    --hidden-import "engineio.async_drivers.asgi" ^
    --collect-all ultralytics ^
    ai_server_test.py

echo Copying assets...
copy .env "dist\DKAI_Server_Final\"
copy front.mp4 "dist\DKAI_Server_Final\"
copy back.mp4 "dist\DKAI_Server_Final\"
if not exist "dist\DKAI_Server_Final\templates" mkdir "dist\DKAI_Server_Final\templates"
copy templates\* "dist\DKAI_Server_Final\templates\"
if not exist "dist\DKAI_Server_Final\images_test" mkdir "dist\DKAI_Server_Final\images_test"
copy images_test\* "dist\DKAI_Server_Final\images_test\"
if not exist "dist\DKAI_Server_Final\outputs" mkdir "dist\DKAI_Server_Final\outputs"

echo Build Complete! Output in dist/DKAI_Server_Final
popd
pause
