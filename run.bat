@echo off

REM go to the project folder
cd /d "C:\Users\Calin\PyCharmProjects\text-editor-project"

REM activate the virtual environment
call venv\Scripts\activate.bat

REM go back to the project root (same as cd ../.. after Scripts)
cd /d "C:\Users\Calin\PyCharmProjects\text-editor-project"

REM run your script
python main.py

REM optional: pause so the window doesn’t close immediately
pause
