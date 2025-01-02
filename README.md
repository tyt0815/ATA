# ATA
 Auto Trading Agent

# 콘다 환경 설치
```
conda env create -f ./environment.yml
conda activate ata
```

# 백그라운드에서 실행 + 출력을 파일에
```
nohup python -u main.py > output.log 2>&1 &
```

# 백그라운드 실행중인 프로그램 종료
```
ps aux | grep main.py
kill -9 ~
```
