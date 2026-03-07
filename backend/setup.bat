@echo off
echo ===================================================
echo    Iniciando o Setup do EditMind (Ambiente Local)
echo ===================================================
echo.

echo [1/3] Criando o ambiente virtual (venv)...
python -m venv venv

echo [2/3] Ativando o ambiente e instalando as dependencias...
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo ===================================================
echo    Ambiente configurado com sucesso!
echo.
echo    Para ligar o motor do backend, digite no terminal:
echo    venv\Scripts\activate
echo    uvicorn main:app --reload
echo ===================================================
pause