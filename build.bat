@echo off
echo ========================================
echo   상품 최저가 검색기 EXE 빌드
echo ========================================
echo.

REM 의존성 설치
echo [1/2] 의존성 설치 중...
pip install -r requirements.txt

echo.
echo [2/2] EXE 파일 빌드 중...
pyinstaller --onefile --windowed --name "상품최저가검색기" price_finder_gui.py

echo.
echo ========================================
echo   빌드 완료!
echo   dist\상품최저가검색기.exe 파일을 사용하세요.
echo.
echo   * 처음 실행 시 API 키 설정 창이 나타납니다.
echo   * 네이버 개발자 센터에서 API 키를 발급받으세요.
echo ========================================
pause
