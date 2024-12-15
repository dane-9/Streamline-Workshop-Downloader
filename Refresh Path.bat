@echo off
:: Refreshes environment variables in the current cmd session

:: Re-import the PATH from the registry
FOR /F "usebackq tokens=2,*" %%A IN (`REG QUERY "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path`) DO (
    SET "PATH=%%B"
)

:: Export the updated PATH to the current session
SET "PATH=%PATH%"
