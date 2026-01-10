@echo off
pushd "%~dp0"
echo Building DK_AI Server TEST VERSION (V2)...
..\venv\Scripts\pyinstaller --noconfirm --onedir --console --name "DKAI_Server_Test_V2" ^
    --add-data "src;src" ^
    --add-data "weights;weights" ^
    --add-data "templates;templates" ^
    --hidden-import "engineio.async_drivers.asgi" ^
    --collect-all ultralytics ^
    ai_server_test.py

echo Copying assets...
copy .env "dist\DKAI_Server_Test_V2\"
copy front.mp4 "dist\DKAI_Server_Test_V2\"
copy back.mp4 "dist\DKAI_Server_Test_V2\"
if not exist "dist\DKAI_Server_Test_V2\templates" mkdir "dist\DKAI_Server_Test_V2\templates"
copy templates\* "dist\DKAI_Server_Test_V2\templates\"
if not exist "dist\DKAI_Server_Test_V2\images_test" mkdir "dist\DKAI_Server_Test_V2\images_test"
copy images_test\* "dist\DKAI_Server_Test_V2\images_test\"

echo Build Complete! Output in dist/DKAI_Server_Test_V2
popd
pause
