import phorce

with phorce.connect() as robot:        # 실물 로봇에 연결 (with 를 쓰면 정리는 자동)
    result = robot.play(1)             # 1번 재생, 끝날 때까지 기다림 — 로봇이 움직입니다!
    print("성공!" if result.ok else result.detail)
