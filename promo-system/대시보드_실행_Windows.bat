@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 처음 실행이면 필요한 프로그램을 설치합니다. 잠시 기다려 주세요...
python -m pip install -q -r requirements.txt
echo 대시보드를 엽니다. 이 창은 닫지 마세요. 끝낼 때 창을 닫으면 됩니다.
python -m streamlit run src\app.py
pause
