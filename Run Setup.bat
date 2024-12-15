@echo off
setlocal EnableDelayedExpansion

:: Define Python version and installer URL
set "PYTHON_VERSION=3.12.7"
set "PYTHON_INSTALLER=python-%PYTHON_VERSION%-amd64.exe"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_INSTALLER%"

:: Function to check Python installation
:CheckPython
echo Checking if Python is installed on your system...
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Python is already installed on your system. Proceeding to upgrade pip...
    goto UpgradePip
) ELSE (
    echo Python is not detected on your system. Proceeding to install Python %PYTHON_VERSION%...
    goto InstallPython
)

:: Function to install Python
:InstallPython
echo Downloading Python %PYTHON_VERSION% installer. This may take a few moments depending on your internet speed...
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'"
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to download Python installer. Please check your internet connection and try again.
    pause
    exit /b 1
)

echo Installing Python %PYTHON_VERSION%. System might prompt with UAC Window.
start /wait "" "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

:: Attempt to refresh PATH in the current session
echo Refreshing environment variables to include Python...
call "%~dp0Refresh Path.bat"

:: Wait and retry mechanism
set "RETRIES=10"
set "DELAY=2"
:WaitForPython
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Python installed successfully! Cleaning up installation files...
    del "%PYTHON_INSTALLER%"
    goto UpgradePip
) ELSE (
    set /a RETRIES-=1
    IF !RETRIES! LEQ 0 (
        echo ERROR: Python installation failed or PATH was not updated correctly.
        echo Attempting to manually add Python to PATH...
        set "DEFAULT_PYTHON_DIR=C:\Program Files\Python%PYTHON_VERSION%"
        IF EXIST "!DEFAULT_PYTHON_DIR!\python.exe" (
            set "PATH=!DEFAULT_PYTHON_DIR!\Scripts;!DEFAULT_PYTHON_DIR!;!PATH!"
            echo Added "!DEFAULT_PYTHON_DIR!\Scripts\" and "!DEFAULT_PYTHON_DIR!\" to PATH manually.
            goto UpgradePip
        ) ELSE (
            echo ERROR: Python executable not found in the default installation directory.
            echo Please verify the installation or install Python manually.
            pause
            exit /b 1
        )
    )
    echo Waiting for Python to be recognized... Retries left: !RETRIES!
    timeout /t !DELAY! >nul
    goto WaitForPython
)

:: Function to upgrade pip
:UpgradePip
echo Upgrading pip to the latest version for better package management...
python -m pip install --upgrade pip
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to upgrade pip. Please check your Python and network configuration.
    pause
    exit /b 1
)
echo Pip upgraded successfully! Moving on to set up the virtual environment...
goto SetupVirtualenv

:: Function to set up the virtual environment using venv
:SetupVirtualenv
echo Checking if the virtual environment already exists in 'Files\Streamline'...
IF NOT EXIST Files\Streamline (
    echo No existing virtual environment found. Creating a new virtual environment named 'Streamline' in the 'Files' directory...
    python -m venv Files\Streamline
    IF %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create virtual environment. Please check your Python installation and try again.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully!
) ELSE (
    echo Virtual environment already exists. Skipping creation...
)

:: Function to activate the virtual environment
:ActivateVirtualenv
echo Activating the virtual environment...
call Files\Streamline\Scripts\activate
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate the virtual environment. Please verify the path and try again.
    pause
    exit /b 1
)
echo Virtual environment activated successfully! Proceeding to install dependencies...
goto InstallDependencies

:: Function to install dependencies
:InstallDependencies
echo Installing required dependencies from 'Files\requirements.txt'...
python -m pip install --upgrade pip
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to upgrade pip within the virtual environment. Please check the environment and try again.
    pause
    exit /b 1
)
python -m pip install -r Files\requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies. Please check the 'Files\requirements.txt' for any issues.
    pause
    exit /b 1
)
echo Dependencies installed successfully! Now creating the launcher script...
goto CreateStreamline

:: Function to create Streamline.bat
:CreateStreamline
echo Creating 'Streamline.bat' launcher script...
(
    echo @echo off
    echo setlocal
    echo.
    echo :: Run downloader.py using the virtual environment's pythonw.exe
    echo start "" "%~dp0Files\Streamline\Scripts\pythonw.exe" "%~dp0downloader.py"
    echo.
    echo :: End the script and close the window
    echo endlocal
    echo exit /b 0
) > "Streamline.bat"
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create 'Streamline.bat'. Please check file permissions and try again.
    pause
    exit /b 1
)
echo 'Streamline.bat' created successfully! Cleanup and finalization in progress...

:: Deleting Setup Files
echo Scheduling silent deletion of setup files for a clean environment...
powershell -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Remove-Item -Path '%~f0', '%~dp0Refresh Path.bat' -Force"

:: Setup Completed
echo Setup complete! You can now run 'Streamline.bat' to launch the application.
PAUSE
