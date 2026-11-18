"""API 키 읽기. 키는 코드에 넣지 않습니다.

찾는 순서: 1) 컴퓨터 환경변수  2) 프로그램 폴더의 '설정.txt'  3) 웹(Streamlit) 비밀 설정
설정.txt 예시 (한 줄에 하나):
    OPENDART_API_KEY=발급받은키
    GEMINI_API_KEY=발급받은키
    관리자_비밀번호=원하는비밀번호
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _설정파일():
    f = ROOT / "설정.txt"
    값 = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                값[k.strip()] = v.strip()
    return 값


def get(name, default=""):
    if os.environ.get(name):
        return os.environ[name]
    v = _설정파일().get(name)
    if v:
        return v
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


def 있음(name):
    return bool(get(name))
