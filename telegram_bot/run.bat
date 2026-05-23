@echo off
chcp 65001 >nul
echo ==============================================
echo Tunika ERP Botni ishga tushirish dasturi
echo ==============================================

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Virtual muhit (venv) yaratilmoqda...
    python -m venv venv
)

echo [2/3] Paketlar tekshirilmoqda...
venv\Scripts\python.exe -m pip install -r requirements.txt

echo [3/3] Bot ishga tushirildi! (To'xtatish uchun CTRL+C bosing)
echo.
venv\Scripts\python.exe bot.py

pause
