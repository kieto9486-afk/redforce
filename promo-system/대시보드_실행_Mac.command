#!/bin/bash
cd "$(dirname "$0")"
echo "필요한 프로그램을 확인합니다..."
python3 -m pip install -q -r requirements.txt
echo "대시보드를 엽니다. 끝낼 때 이 창을 닫으세요."
python3 -m streamlit run src/app.py
