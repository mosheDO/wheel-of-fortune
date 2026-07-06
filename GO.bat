@REM @echo off
@REM set "BASE=%~dp0"

@REM "%BASE%Locale.Emulator.2.5.0.1\LEProc.exe" -runas "81d887e0-08ab-42ed-8b06-d16f360ccba6" "C:\Windows\System32\cmd.exe" "/c cd /d C:\WHEEL && ""%BASE%otvdm-v0.9.0\otvdm.exe"" WHEEL.EXE"


@echo off
set "BASE=%~dp0"

if not exist "C:\WHEEL" (
    echo Copying WHEEL folder to C:\...
    xcopy "%BASE%WHEEL" "C:\WHEEL" /E /I /H /Y
    echo Copy complete!
) else (
    echo WHEEL folder already exists in C:\
)

echo.
echo Running game...
"%BASE%Locale.Emulator.2.5.0.1\LEProc.exe" -runas "81d887e0-08ab-42ed-8b06-d16f360ccba6" "C:\Windows\System32\cmd.exe" "/c cd /d C:\WHEEL && ""%BASE%otvdm-v0.9.0\otvdm.exe"" WHEEL.EXE"
