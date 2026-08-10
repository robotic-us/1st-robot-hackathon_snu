# phorce 해커톤 핵심 참조 (Condensed)

> 원본: 01-quickstart, 02-tutorial, 03-manual, pcm-board-guide, phorce-studio-hackathon-manual, 제1회 사전 기술 가이드라인, GaP, ASAP, DREAM-Chunk
> 목적: 이 문서만 보고도 Jetson→pcm→phact 로봇을 켜고, 동작을 재생하고, 피드백 기반 코드를 짤 수 있도록 압축

**프로젝트 목표:** 흐트러진 신발을 한 쌍씩 수거·정리하고, 요청받은 신발을 다시 꺼내 제시하는 로봇 팔 기반 **shoe valet**을 만든다.

**문서 우선순위:** 실제 참가자 API에 관한 충돌이 있으면 `03-manual`과 현재 로봇의 `phorce list/status`를 우선한다. 사전 기술 가이드라인과 연구 논문은 설계 영감이며, 공개되지 않은 저수준 제어 API를 사용할 수 있다는 근거가 아니다.

---

## 1. 시스템 개요

| 부품 | 역할 | 비유 |
|------|------|------|
| Jetson (젯슨) | 코드를 돌리는 컴퓨터 | 뇌 |
| pcm | Jetson ↔ 모터 중계기, EtherCAT 슬레이브, SD 카드 보관 | 신경/중앙관리자 |
| phact (최대 12축) | 관절 모터 드라이버 | 근육 |

- **피드백(⬆️)**: `/phorce/feedback` 토픽의 고정 길이 `AxisFeedback[12]`를 **1kHz**로 수신. 실제로 연결된 축은 `valid`와 비트 마스크로 구분
- **명령(⬇️)**: 미리 저장된 **모션 슬롯 ID 1~50** 중 하나를 재생. 참가자는 관절을 직접 제어하지 않음.

---

## 2. 물리적 안전 & PCM 보드 조작

### PCM LED 상태

| 색 | 뜻 | 행동 |
|---|---|---|
| 파랑 | 부팅/준비 중 | 기다리기 |
| 초록 | 파킹(힘 빠짐, 안전) | 설정/교시 가능 |
| 노랑 | 힘 들어감 or 동작 중 | **물러서기** |
| 흰색 | 종료 중 | 기다리기 |
| 빨강 | 에러/E-stop | 안내 음성·Studio 원인 확인. E-stop은 전원 재투입 필요 |

### 버튼

| 버튼 | 동작 | 주의 |
|---|---|---|
| **기능 버튼 1** (약 1초 꾹) | "움직임 시작": 3초 경고 후 서보 ON → 설정된 부팅 자세 → 노랑 | 최소 0.6초. 부팅 직후 1+2 동시 누른 금지(시험모드) |
| **기능 버튼 2** (1초 꾹) | "끄기": 종료 자세 → 흰불 → 전원 분리 | |
| **E-Stop 스위치** | 모터 전원 즉시 차단 | 한 번 누르면 **전원 껐다 켜야** 풀림 |

### 안전 체크리스트

- 실물 명령 전 반드시 주변 확인
- 급하면 **물리 E-Stop** (키보드/코드 cancel 아님)
- "준비 안 됨" → 버튼 1 누르기
- "복구 필요" → 버튼 2(파킹) → 다시 버튼 1
- 부팅 중 "관절을 살짝 움직여 주세요" 안내가 반복되면 각 관절을 조금씩 움직여 자세 탐색을 완료
- SD 카드는 pcm 전원을 끈 뒤에만 물리적으로 분리
- 빨간불 원인이 저장된 축 구성과 실제 연결 축 불일치라면 Studio에서 구성을 다시 저장하거나 해제한 뒤 재부팅

---

## 3. 모션 슬롯 계약

- 사용 가능 ID: **1~50** (0은 sentinel, play 금지)
- 한 번에 **하나의 동작만** 재생 (max sequence length = 1, 큐 없음)
- 모션 카탈로그의 진짜 원본은 **pcm 내부의 SD 카드/슬롯** — Jetson 파일 아님
- 새 동작은 **phorce Studio**로 교시(손으로 움직여 녹화)해서 pcm에 저장
- 참가자 런타임 API는 `motion_id`만 선택한다. 속도·강성·관절 위치·토크·게인·궤적 파라미터를 함께 보낼 수 없음
- 실행 중인 모션 내부의 샘플이나 궤적을 다른 모션과 실시간으로 교체할 수 없음. 반응성을 높이려면 짧고 안전한 모션 슬롯을 설계하고 **슬롯 경계에서** 다시 판단
- `cancel()`은 E-Stop이 아니며 실물에서 거부될 수 있으므로 안전 정지 수단으로 가정하지 않음

---

## 4. CLI 명령

```bash
# 시스템 진단
phorce doctor

# 재생 가능한 모션 목록 (로봇 적재 슬롯 기준)
phorce list

# 모션 재생 (블로킹, 30s 타임아웃)
phorce play 1

# 상태 확인
phorce status

# 시뮬레이터에서 연습
phorce play 1 --target sim:demo

# GUI
phorce-console
```

- 공통 플래그: `--target robot|sim:SESSION`, `--namespace`, `--domain-id`, `--timeout <초>`, `--json`
- 종료 코드: 0 성공 / 1 거부·실패 / 2 사용법 / 3 게이트웨이 없음 / 4 타임아웃 / 5 BUSY / 130 Ctrl+C

---

## 5. Python API (권장)

```python
import phorce
import time

latest = {"pos0": None}

def on_feedback(fb):
    a0 = fb.axis[0]
    if a0.valid:                    # ★ valid 먼저 확인
        latest["pos0"] = a0.position_rad

# 연결
with phorce.connect() as robot:                 # 실물
# with phorce.connect("sim:demo") as robot:     # 시뮬

    # 상태
    status = robot.status()
    print(status.ethercat_operational, status.estop_active)

    # 카탈로그
    for m in robot.motions():
        print(m.id, m.name)

    # 1) 동기 재생
    result = robot.play(1)
    print(result.ok)        # 속성(attribute), ok() 아님

    # 2) 비동기 재생
    handle = robot.play_async(2, on_feedback=on_feedback)
    handle.wait(timeout=30)

    # 3) 피드백 콜백
    robot.watch(on_feedback)

    # 느린 판단 루프 (~2Hz). 히스테리시스로 같은 모션의 무한 반복 방지.
    armed = True
    while True:
        time.sleep(0.5)
        p = latest["pos0"]
        if p is None:
            continue
        if armed and p > 0.5:
            try:
                robot.play(2)
                armed = False
            except phorce.MotionBusy:
                pass
        elif p < 0.4:
            armed = True
```

### 예외

- `MotionBusy`: 지금 다른 동작 중 → 기다렸다 재시도
- `MotionRejected`: 거절 상세 코드 확인. 코드 12·13만 사람의 버튼 개입이 필수이며, 나머지는 형식·상태·축 문제에 맞게 대응
- `MotionAborted`: 재생 중 중단 → 복구 절차 따르기

### rclpy 직접 구독

```python
from rclpy.qos import qos_profile_sensor_data
from agx_msgs.msg import PhorceFeedback

node.create_subscription(
    PhorceFeedback, "/phorce/feedback", cb, qos_profile_sensor_data  # ★ 필수
)
```

---

## 6. C++ API

```cmake
find_package(phorce_cpp REQUIRED)
target_link_libraries(my_node phorce_cpp::motion_client)
```

```cpp
#include "phorce_cpp/motion_client.hpp"
auto client = phorce::MotionClient::attach(node, phorce::Target::robot());
auto op = client->play_async(7);
auto fut = op->result();

// 타이머/루프에서 논블로킹 확인
if (fut.wait_for(0ms) == std::future_status::ready) {
    auto r = fut.get();
    if (r.ok()) { /* 성공 */ }
    else if (r.busy()) { /* BUSY → 재시도 */ }
    else if (r.needs_operator()) { /* 버튼 필요 */ }
}
```

- 상수: `kMinMotionId=1`, `kMaxMotionId=50`, `kNoMotionId=0`, `kMaxSequenceLength=1`, `kStateFreshLimitMs=1500`
- 저수준 EtherCAT 프로그램을 직접 빌드하면 `setcap` 권한이 날아감 → `sudo agr-setcap-ethercat <바이너리>` 재실행
- 모션 슬롯 API만 쓰면 권한 문제 없음

---

## 7. ROS 2 인터페이스 요약

| 이름 | 종류 | 속도·QoS | 용도 |
|---|---|---|---|
| `/phorce/feedback` | topic `PhorceFeedback` | **1kHz**, `sensor_data` | 12축 실시간 상태 |
| `/phorce/status` | topic `PhorceStatus` | 10Hz, reliable | 전체 상태 요약 |
| `/phorce/motion_window` | topic `MotionWindowStatus` | 2Hz, latched | 카탈로그 조회 |
| `/motion_action_server/play_motion_sequence` | action `PlayMotionSequence` | — | **유일한 구동 API** |
| `/motion_slot_state` | topic `MotionSlotState` | — | 슬롯 비트맵·busy |
| `~/list_motion_slots` | service `ListMotionSlots` | — | 슬롯 목록 |

Raw action 호출 예:
```bash
ros2 action send_goal /motion_action_server/play_motion_sequence \
  agx_msgs/action/PlayMotionSequence "{motion_ids: [1], stop_on_error: true}" -f
```

---

## 8. 피드백 필드 (AxisFeedback[12])

필수만:
- `position_rad` — 관절 각도
- `velocity_rad_s` — 각속도
- `current_a` — 모터 전류(A). 부하 변화의 간접 지표
- `dob_a` — 외란 관측기 추정값(A). 직접 측정한 토크나 힘이 아님
- `bus_v` — 버스 전압
- `temp_c` — 온도
- `kp_echo` / `kd_echo` — 현재 적용 중인 게인의 되울림(읽기 전용)
- `valid` — **이 축 데이터를 믿어도 되는 유일한 증거**
- `stale` / `fault` / `oper` — 오래됨/결함/운전중

⚠️ `!stale`로는 부족함. 한 번도 안 온 축은 stale도 아니기 때문.

프레임 수준에는 `wkc`, `tx_cycle_seq`, `axis_valid_mask`, `axis_stale_mask`, `axis_oper_mask`, `axis_fault_mask`, `am_rx_age_ms`, `status_flags`도 있다.

### 접촉·걸림 판정 원칙

- `current_a` 또는 `dob_a` 하나를 외력·관절 토크와 동일시하지 않음
- 축·모션·진행 구간별 정상 기준선을 실험으로 기록하고, 짧은 윈도우의 변화량·지속시간·속도 저하·진행 정체를 함께 사용
- 임계값에는 지속 조건과 히스테리시스를 적용해 순간 노이즈로 복구 모션이 발동하지 않게 함
- 모든 통계는 `valid=true`인 샘플로만 계산

---

## 9. 거절 코드 (PlayMotionSequence)

| 코드 | 이름 | 뜻 | 대응 |
|---|---|---|---|
| 5 | QUEUE_FULL / BUSY | 지금 바쁨 | **기다리면 풀림**, 재시도 루프 OK |
| 12 | NOT_READY_FOR_MOTION | 준비 안 됨 | 버튼 1 (0.6초) → 3초 대기 |
| 13 | RECOVERY_REQUIRED | 복구 필요 | 버튼 2(파킹) → 다시 버튼 1 |
| 4 | MOTION_ID_NOT_LOADED | 로드 안 된 ID | `phorce list`에서 실제 ID 확인 |
| 3 | MOTION_ID_RANGE | 1~50 범위 밖 | ID 확인 |
| 6·11 | MASTER_NOT_OP / AXIS_NOT_OPERATIONAL | EtherCAT/축 문제 | 배선·전원 점검 |
| 0·1·2 | NONE / EMPTY / TOO_LONG | 요청 형식 문제 | 단일 ID 요청인지 확인 |
| 7·8·9·10 | COMMAND_SOURCE / STATE_STALE / SUPERVISOR_VETO / CONTRACT_NOT_ACTIVE | 명령 권한·상태·안전 계약 문제 | `detail`, `phorce doctor`, 상태 신선도 확인 |

재시도 루프는 코드 5에서만 사용한다. 코드 12·13은 기다려도 풀리지 않으며, 다른 코드는 원인을 고치기 전 자동 재시도하지 않는다.

### 게이트웨이 안전 경계

- 모든 하행 명령은 하드 veto, 상태 신선도, NaN, 한계, 변화율 등 게이트웨이 안전 검사를 통과해야 함
- 참가자 모션 슬롯 API는 이 보호 계층을 우회할 수 없음
- 상위 판단 코드나 LLM이 멈춰도 임의의 저수준 명령을 계속 보내는 구조가 아니어야 함

---

## 10. 흔한 실수 & 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| 피드백 안 옴 (에러 없음) | QoS 누락 | `qos_profile_sensor_data` 사용 |
| 거의 다 BUSY | 1kHz 콜백에서 `play()` 호출 | 느린 루프(~0.5s)로 이동 |
| "준비 안 됨" 반복 | 버튼 1 안 누름 | 사람이 0.6초 이상 누르기 |
| `phorce: command not found` | 환경 미로드 | 재로그인 또는 보드 재검수 |
| C++ 재빌드 후 권한 오류 | setcap 날아감 | `sudo agr-setcap-ethercat <바이너리>` |
| 로봇 안 움직임 (에러 없음) | sim 대상 | `--target robot` 확인 |

---

## 11. phorce Studio 사용 흐름

Studio = 로봇에 **사전 설정을 심는 도구** (노트북 아님, 로봇에 저장됨).

1. **USB**로 노트북–pcm 연결
2. **① 설정**: 축 구성 → 이름 → **영점(0도)** → 부팅 자세 → 종료 자세 → 저장
   - 영점은 교시 **전에** 잡아야 함. 나중에 바꾸면 저장된 동작이 어긋남.
3. **② 교시**: 서보 끄기 → 녹화 시작 → 손으로 천천히 움직임 → 종료 → 확인 → **SD 카드에 저장**
4. **③ 모니터**: 실시간 그래프, 게인 임시 적용/저장

핵심 원칙:
- **힘 빼고 가르치고, 힘 켜고 재생한다**
- **저장 = 로봇에 각인**: 설정은 pcm FLASH, 동작은 SD 카드에 남음
- 로봇이 실제 움직이는 버튼은 **[로봇에서 재생]** 하나만
- Studio의 화면 재생은 미리보기일 뿐 로봇이 움직이지 않으며, 실제 동작은 ⑤ 단계의 **[로봇에서 재생]**에서만 발생
- 위치 PID의 **적용**은 전원 재투입 시 사라지는 시험값이고, **설정 저장**은 phact 메모리에 영구 반영됨
- 저장 중 SD 드라이브가 잠시 사라지는 것은 Studio와 pcm이 번갈아 접근하기 때문일 수 있으므로 화면 안내가 끝날 때까지 기다림

---

## 12. SOTA 논문과 phorce에서 가능한 적용

사전 기술 가이드라인의 저수준 제어 예시는 연구 방향을 설명한 것이다. 참가자 API가 모션 슬롯 선택만 허용한다는 최신 플랫폼 계약에 맞춰 아래처럼 재해석한다.

| 논문 | 논문이 실제로 하는 일 | phorce에서 가능한 적용 | 그대로 구현할 수 없는 부분 |
|---|---|---|---|
| **GaP** | LLM/VLM 코딩 에이전트가 모듈형 스킬의 방향성 계산 그래프를 만들고, 내부 시뮬레이션 리허설로 그래프 구조와 파라미터를 반복 개선한 뒤 에지 인터프리터에 배포 | 각 스킬을 승인된 `motion_id` 호출로 제한한 Behavior Graph. 시뮬레이션·기록된 실험으로 그래프를 오프라인 개선하고, 런타임 LLM은 이벤트 기반의 제한된 다음 슬롯 제안만 수행 | 논문의 self-learning을 "실물 1kHz 루프에서 LLM이 즉시 제어값을 튜닝"하는 방식으로 설명하면 부정확 |
| **ASAP** | 실제 롤아웃으로 delta-action 모델을 학습하고 이를 **시뮬레이터에 넣어** 정책을 미세조정. 최종 실물 배포에는 delta 모델 없이 미세조정된 정책을 사용 | 시뮬레이션과 실물의 모션별 피드백 차이를 오프라인 분석해 모션 녹화·Studio 설정·접촉 기준선·슬롯 선택 규칙을 개선하는 영감 | 참가자 런타임에서 `nominal + delta` 관절 명령을 1kHz로 모터에 보낼 수 없음 |
| **DREAM-Chunk** | 고정 VLA에서 여러 액션 청크를 샘플링하고 경량 세계 모델로 잠재 미래를 예측한 뒤, 매 스텝 실제 잠재 상태와 가장 잘 맞는 phase-aligned 액션을 선택 | 짧은 안전 모션 슬롯을 coarse chunk로 보고, 슬롯 종료 후 피드백 윈도우와 작업 상태에 가장 맞는 다음 슬롯을 선택 | 정적 사전녹화 Dictionary가 논문의 후보 생성 방식은 아니며, 공개 API로 실행 중 슬롯의 개별 액션을 교체하거나 토크·임피던스 기준으로 궤적을 스위칭할 수 없음 |

### 실전 결론

- **GaP가 주 아키텍처:** 해석 가능한 Behavior Graph와 명시적 성공·실패 분기
- **DREAM-Chunk는 슬롯 경계 반응성의 영감:** 짧은 모션 후보와 관측 기반 다음 슬롯 선택
- **ASAP는 오프라인 분석의 영감:** 실물 로그로 기준선·모션 라이브러리·시뮬레이션을 개선
- 어떤 논문도 참가자 API 계약을 확장하지 않음

---

## 13. 예제 코드 위치

```bash
# Python/C++ 예제
EX="$(ros2 pkg prefix phorce)/share/phorce/examples"
ls "$EX"
# python3 "$EX/01_first_motion.py" 1
# python3 "$EX/02_read_feedback.py"
# python3 "$EX/03_feedback_to_motion.py"

ros2 run phorce_cpp phorce_example_01_first_motion 1
```

---

## 14. 막혔을 때 진단 패킷

```bash
phorce doctor --json
phorce list --json
```

두 줄 결과를 운영진에게 보여주기.

---

## 15. 추가 인사이트: AI Motion Director 설계

> 출처: `해커톤 문서 .md` — 참가자가 직접 관절을 제어하지 않고 **미리 녹화된 모션 ID를 선택하는 결정자(decision maker)** 로 설계해야 함.

### 15.1 핵심 발견

- 참가자는 개별 관절을 제어하지 않음. 오직 **Motion ID 1~50 중 하나를 선택**.
- 전체 로직은 `Observe → Decide → play(motion_id) → Observe Again` 의 **Behavior Tree**.
- **빠른 루프(1kHz)**: 피드백만 저장. **느린 루프(~2Hz, 0.5초 간격)**: 판단·모션 실행.
- 피드백의 `current_a`와 `dob_a`를 모션별 기준선과 비교하면 **접촉 후보 이벤트**를 만들 수 있음. 둘 다 직접 힘·토크 측정값은 아님.
- P/F/I 벡터 편집, 관절 스트리밍은 참가자 API가 아님 — 미리 Studio에서 설정.

### 15.2 모션 슬롯 전용 Physical AI 아키텍처

```
Layer 3  선택적 LLM 조언
         실패 설명·승인된 다음 스킬 추천·operator 요청
                         ↓ MotionDecision 후보

Layer 2  결정론적 Behavior Graph + Motion Selector
         상태 전이·카탈로그/화이트리스트 검증·재시도 제한
                         ↓ play(motion_id)

────────────── 참가자 API 경계 ──────────────

Layer 1  phorce Gateway + pcm
         안전 검사 후 사전 녹화된 슬롯을 그대로 재생
                         ↓
                      실제 로봇

         1kHz Feedback ────────────────→ 관측 윈도우
```

| 계층 | 주기 | 역할 |
|------|------|------|
| 1kHz 관측 콜백 | 약 1kHz | `valid` 샘플만 최신 버퍼·통계 윈도우에 저장. 여기서 LLM이나 `play()`를 호출하지 않음 |
| Behavior Graph / Motion Selector | 이벤트 기반 또는 약 2Hz | 작업 상태, 모션 결과, 접촉 후보 이벤트를 보고 허용된 다음 `motion_id` 하나를 결정 |
| LLM 조언 | 의미 있는 실패 이벤트에서만 | 승인된 후보 중 선택·설명·operator 요청. 결과는 로컬 스키마와 그래프 전이 규칙으로 검증 |
| phorce Gateway / pcm | 플랫폼 관리 | 참가자 요청을 안전 검사하고 SD 카드의 사전 녹화 모션을 재생. 참가자가 대체 구현하지 않음 |

**계층 간 인터페이스**

```
SelectorInput {
  graph_state,
  live_motion_catalog,
  allowed_next_motion_ids,
  robot_status,
  feedback_window_statistics,
  last_motion_result,
  retry_history
}

MotionDecision {
  action: play_motion | no_action | operator_required,
  motion_id: integer | null,
  reason,
  confidence
}

실행 가능한 유일한 하행 값: 검증된 motion_id 하나
```

### 15.3 권장 소프트웨어 구조

```
Camera / Sensor
       ↓
   Perception
       ↓
Behavior Graph (state machine)
       ↓
Motion Selector (deterministic + LLM fallback)
       ↓
   Motion ID
       ↓
   phorce
       ↓
   Robot
```

### 15.4 지식 기반(Knowledge Base) + OpenAI File Search

LLM에 프로젝트 지식을 넘기되, 매번 전체 문서를 읽히지 않고 **File Search**로 필요한 내용만 검색.

> 이 절의 OpenAI API 내용은 로봇 PDF의 근거가 아니다. 실제 구현 전 현재 공식 OpenAI 문서와 설치된 SDK 버전으로 API 형식을 다시 확인한다.

**폴드 구조 예시**

```
knowledge/
├── 00_AI_OPERATING_RULES.md      # 모델이 "어떻게" 사용할지 규칙
├── 01_HACKATHON_CONTEXT.md
├── 02_PHORCE_PLATFORM.md
├── 03_PHACT_HARDWARE.md
├── 04_MOTION_DESIGN_GUIDE.md
├── 05_FAILURE_RECOVERY_PLAYBOOK.md
├── 06_RESEARCH_PAPER_NOTES.md
├── 07_VERIFIED_EXPERIMENTS.md
├── motion_library.json
├── behavior_graph.json
└── *.pdf (원본 매뉴얼들)
```

**File Search 연동 개요**

1. `build_knowledge_base.py`로 `knowledge/` 폴드를 OpenAI vector store에 업로드.
2. `KnowledgeBackedMotionSelector`에서 `responses.create(..., tools=[{"type": "file_search", ...}])` 호출.
3. 출력은 JSON 스키마로 강제: `action`, `motion_id`, `reason`, `confidence`, `basis`.
4. **로컬 검증 필수**: 모델이 고른 `motion_id`가 실제 `phorce list` 카탈로그에 있는지 확인.

### 15.5 AI 운영 규칙 (핵심만)

**절대 하지 말 것**

- 존재하지 않는 모션 ID를 지어내지 않기
- 관절·토크·전류·게인·속도 배율·강성 배율·궤적·액추에이터 명령을 직접 내리지 않기
- Behavior Graph나 operator-required 상태를 우회하지 않기
- `valid=false`인 축 데이터를 신뢰하지 않기
- 모터 전류를 외력과 동일시하지 않기

**선호 행동 (정보 불충분 시)**

- 아무것도 하지 않음(no_action)
- 안전한 복구 동작
- 저에너지 홈(home)
- operator 개입 요청

### 15.6 실험 기록 형식

`07_VERIFIED_EXPERIMENTS.md`에 다음 형식으로 기록 → LLM이 과거 성공 사례를 참고.

```markdown
## EXP-YYYYMMDD-NNN
### Configuration
- Robot: ..., Motion ID: ..., Graph state: ..., Git commit: ...
### Observation
- `current_a`/`dob_a`/속도/위치 변화 (`valid=true` 샘플만)
### Result
- 성공/실패/중단
### Verified cause
- 원인 + 증거(영상, 반복 패턴, 물리 점검)
### Successful recovery
- 사용한 모션 ID, 재시도 결과
### Current conclusion
- 다음에 적용할 규칙, confidence
```

### 15.7 런타임 호출 원칙

- **Engineering copilot** 모드: 전체 지식 검색 가능.
- **Runtime recovery selector** 모드: 현재 graph state, 현재 모션 ID, 허용된 다음 모션, 실패 요약, feedback-window 통계, 재시도 이력만 전달.
- LLM은 **1kHz나 5Hz 연속 호출 금지**. 의미 있는 이벤트 발생 시 1회 호출 → 로컬 검증 → 실행.

---

## 16. Shoe Valet 모션 라이브러리와 Behavior Graph

> **출처와 상태: ChatGPT 브레인스토밍 제안 — 검증·승인되지 않음.** 이 절 전체(anchors, motion IDs, behavior sequences, metadata, recording order)는 대화 중 ChatGPT가 제안한 초기 설계안이다. 사용자 결정, 실제 로봇 사양, 운영진 요구사항 또는 검증된 구현으로 취급하지 않는다. 당시에는 두 신발을 동시에 드는 peg 기반 개념을 가정했지만, 이후 논의에서는 **신발 한 짝씩 처리하는 고정 V형 end effector**가 유력해졌다. 따라서 아래 anchor와 slot map을 그대로 구현하거나 실제 PCM에 기록하지 말고, 기구와 pickup 방식이 확정된 뒤 Section 17의 최신 결정사항과 실물 시험 결과를 기준으로 새로 승인한다.

이 메커니즘의 모션 라이브러리는 `lift`, `rotate`, `lower` 같은 동사 목록이 아니라, 검증된 **전신 자세(full-robot pose) 사이의 방향성 전이 그래프**로 설계한다.

Studio 교시는 설정된 모든 관절 위치를 함께 기록한다. 예를 들어 intake 방향에서 녹화한 모션에는 그때의 yaw 위치도 포함된다. 따라서 각 모션에는 알려진 **전체 시작 자세**, **전체 종료 자세**, **전후 payload 상태**가 있어야 한다. 참가자 API는 ID 1~50 중 저장된 모션 하나만 실행하며 큐는 없다.

> 모든 모션은 안전하게 일시 정지하고 피드백을 검사한 뒤 다음 행동을 결정할 수 있는 자세에서 끝나야 한다.

### 16.1 Anchor pose 정의

모션을 녹화하기 전에 아래 anchor를 물리적으로 교시하고 사진·관절 상태·기구 설정과 함께 문서화한다.

| Anchor | 의미 | Payload |
|---|---|---|
| `H0_HOME` | 지지 cradle 위에 팔을 접고, yaw 중앙, peg 수축 | 없음 |
| `I0_INTAKE_READY` | intake 위에서 peg가 신발 입구 바로 바깥에 정렬 | 없음 |
| `I1_INTAKE_PROBED` | peg를 약 10~15 mm만 삽입 | 없음 |
| `I2_INTAKE_INSERTED` | peg 완전 삽입, 신발은 intake mat에 놓인 상태 | 없음 |
| `I3_PAIR_HELD` | 신발 두 짝을 약 50~70 mm 들어 올림 | 한 쌍 |
| `A0_SLOT_A_HOVER` | 한 쌍을 보관 슬롯 A 위에 듦 | 한 쌍 |
| `A1_SLOT_A_RESTING` | 신발은 A rail에 놓이고 peg는 삽입된 상태 | 선반이 지지하는 한 쌍 |
| `A2_SLOT_A_CLEAR` | 신발 보관 완료, peg 수축, 팔은 슬롯에서 벗어남 | 없음 |
| `B0_SLOT_B_HOVER` | 한 쌍을 보관 슬롯 B 위에 듦 | 한 쌍 |
| `B1_SLOT_B_RESTING` | 신발은 B rail에 놓이고 peg는 삽입된 상태 | 선반이 지지하는 한 쌍 |
| `B2_SLOT_B_CLEAR` | 신발 보관 완료, peg 수축, 팔은 슬롯에서 벗어남 | 없음 |
| `AP0_A_PICK_READY` | 빈 peg가 A에 보관된 신발 바깥에 정렬 | 없음 |
| `AP1_A_PICK_PROBED` | peg가 A의 신발에 일부 삽입 | 없음 |
| `AP2_A_PICK_INSERTED` | peg가 A의 신발에 완전히 삽입 | 없음 |
| `AP3_A_PAIR_HELD` | A에서 신발 한 쌍을 들어 올림 | 한 쌍 |
| `BP0`–`BP3` | 슬롯 B의 대응 retrieval anchor | 단계에 따라 다름 |
| `P0_PRESENT_HOVER` | 회수한 신발을 customer presentation mat 위에 듦 | 한 쌍 |
| `P1_PRESENTED` | 신발은 mat에 놓이고 peg는 아직 삽입된 상태 | mat가 지지하는 한 쌍 |
| `S0_SERVICE` | 점검하기 쉽게 메커니즘을 연 자세 | 없음 |

`H0_HOME`은 특히 저에너지 자세여야 한다. 출력 구조물이 cradle에 기대도록 해 shoulder actuator가 팔을 계속 들어 올리지 않게 한다.

**Anchor 불변조건:** 위 표는 정상 상태를 뜻한다. 한 짝만 들림, 신발이 비틀림, peg 한쪽만 삽입됨 같은 실패 상태는 정상 `I3`/`AP3`로 간주하지 않는다. 해당 비정상 자세에서 별도로 반복 검증된 recovery motion이 없으면 `operator_required`로 전이한다.

### 16.2 권장 모션 슬롯 맵

압박 상황에서도 쉽게 파악하도록 ID를 기능별 범위로 묶는다. 실제 사용 전 각 ID와 이름이 현재 `phorce list` 결과와 일치하는지 확인한다.

#### IDs 1–9: 공통 intake와 presentation

| ID | Motion name | Start → End | 목적 |
|---:|---|---|---|
| 1 | `home_to_intake_ready` | `H0 → I0` | 신발 intake로 이동 |
| 2 | `intake_probe_15mm` | `I0 → I1` | 짧고 부드러운 삽입 시험 |
| 3 | `intake_probe_retract` | `I1 → I0` | probe 실패 후 후퇴 |
| 4 | `intake_insert_full` | `I1 → I2` | peg 완전 삽입 |
| 5 | `intake_lift_pair` | `I2 → I3` | mat에서 두 신발을 들어 올림 |
| 6 | `intake_ready_to_home` | `I0 → H0` | 수거하지 않을 때 home 복귀 |
| 7 | `intake_held_abort_lower` | `I3 → P1` | pickup 중단 시 신발을 다시 내려놓음 |
| 8 | `presented_retract_home` | `P1 → H0` | peg를 빼고 팔을 home으로 접음 |
| 9 | Reserved | — | intake 개선용 여유 슬롯 |

긴 삽입 모션을 중간에 안전하게 끊을 수 있다고 가정하지 않는다. 짧은 probe를 실행하고 피드백 윈도우를 분석한 뒤에만 full insertion을 허용한다.

#### IDs 10–19: slot A

| ID | Motion name | Start → End | 목적 |
|---:|---|---|---|
| 10 | `held_to_A_hover` | `I3 → A0` | 들어온 한 쌍을 A로 운반 |
| 11 | `A_lower_to_rails` | `A0 → A1` | 밑창을 shelf rail에 놓음 |
| 12 | `A_relift_from_rails` | `A1 → A0` | 배치 검증 실패 시 다시 들어 올림 |
| 13 | `A_retract_clear` | `A1 → A2` | 배치 성공 후 peg를 뺌 |
| 14 | `A_clear_to_home` | `A2 → H0` | 보관 후 home 복귀 |
| 15 | `home_to_A_pick_ready` | `H0 → AP0` | A에 보관된 신발로 접근 |
| 16 | `A_pick_probe_15mm` | `AP0 → AP1` | 부드러운 retrieval probe |
| 17 | `A_pick_probe_retract` | `AP1 → AP0` | probe 실패 후 후퇴 |
| 18 | `A_pick_insert_full` | `AP1 → AP2` | retrieval을 위해 완전 삽입 |
| 19 | `A_pick_lift` | `AP2 → AP3` | A에서 한 쌍을 들어 올림 |

#### IDs 20–29: slot B

| ID | Motion name | Start → End | 목적 |
|---:|---|---|---|
| 20 | `held_to_B_hover` | `I3 → B0` | 들어온 한 쌍을 B로 운반 |
| 21 | `B_lower_to_rails` | `B0 → B1` | 밑창을 shelf rail에 놓음 |
| 22 | `B_relift_from_rails` | `B1 → B0` | 잘못된 배치 후 다시 들어 올림 |
| 23 | `B_retract_clear` | `B1 → B2` | 배치 성공 후 peg를 뺌 |
| 24 | `B_clear_to_home` | `B2 → H0` | 보관 후 home 복귀 |
| 25 | `home_to_B_pick_ready` | `H0 → BP0` | B에 보관된 신발로 접근 |
| 26 | `B_pick_probe_15mm` | `BP0 → BP1` | 부드러운 retrieval probe |
| 27 | `B_pick_probe_retract` | `BP1 → BP0` | probe 실패 후 후퇴 |
| 28 | `B_pick_insert_full` | `BP1 → BP2` | retrieval을 위해 완전 삽입 |
| 29 | `B_pick_lift` | `BP2 → BP3` | B에서 한 쌍을 들어 올림 |

#### IDs 30–39: presentation과 recovery

| ID | Motion name | Start → End | 목적 |
|---:|---|---|---|
| 30 | `A_held_to_present_hover` | `AP3 → P0` | A에서 회수한 한 쌍을 customer 쪽으로 운반 |
| 31 | `B_held_to_present_hover` | `BP3 → P0` | B에서 회수한 한 쌍을 customer 쪽으로 운반 |
| 32 | `present_lower_pair` | `P0 → P1` | 회수한 신발을 mat에 놓음 |
| 33 | `A_restore_after_pick_failure` | `AP3 → A1` | 신발을 A에 안전하게 되돌림 |
| 34 | `B_restore_after_pick_failure` | `BP3 → B1` | 신발을 B에 안전하게 되돌림 |
| 35 | `A_store_abort_to_present` | `A0 → P0` | A가 받을 수 없을 때 들어온 신발을 반환 |
| 36 | `B_store_abort_to_present` | `B0 → P0` | B가 받을 수 없을 때 들어온 신발을 반환 |
| 37 | `A_pick_ready_to_home` | `AP0 → H0` | A probe 실패 후 복귀 |
| 38 | `B_pick_ready_to_home` | `BP0 → H0` | B probe 실패 후 복귀 |
| 39 | Reserved | — | recovery 개선용 여유 슬롯 |

#### IDs 40–49: 확장용

다음 용도를 위해 비워 둔다.

- 세 번째 보관 슬롯
- 다른 신발 폭 설정
- 작은 peg `wiggle` recovery
- presentation flourish
- calibration motion

50개를 쓸 수 있다는 이유만으로 모든 슬롯을 채우지 않는다. ID 50도 사용 가능하지만 현재는 예비 슬롯으로 남긴다.

### 16.3 상위 Behavior sequence

Behavior manager는 매번 모션 하나만 실행하고 결과와 피드백을 확인한 뒤 다음 요청을 보낸다.

#### 한 쌍을 slot A에 보관

```text
1  home_to_intake_ready
2  intake_probe_15mm
   ↓ probe feedback 분석

probe가 정상이면:
4  intake_insert_full
5  intake_lift_pair
   ↓ camera로 두 신발이 모두 들렸는지 확인
10 held_to_A_hover
11 A_lower_to_rails
   ↓ camera로 두 신발이 rail에 지지되는지 확인
13 A_retract_clear
14 A_clear_to_home
```

Probe 실패:

```text
3 intake_probe_retract
6 intake_ready_to_home
→ customer에게 신발 재배치 요청
```

A 배치 실패:

```text
12 A_relift_from_rails
35 A_store_abort_to_present
32 present_lower_pair
8  presented_retract_home
```

#### 한 쌍을 slot B에 보관

```text
1 → 2 → check → 4 → 5 → 20 → 21 → check → 23 → 24
```

#### Slot A에서 회수

```text
15 home_to_A_pick_ready
16 A_pick_probe_15mm
   ↓ probe feedback 분석

정상이면:
18 A_pick_insert_full
19 A_pick_lift
   ↓ camera로 두 신발이 모두 들렸는지 확인
30 A_held_to_present_hover
32 present_lower_pair
   ↓ camera로 두 신발이 mat에 놓였는지 확인
8  presented_retract_home
```

Retrieval probe 실패:

```text
17 A_pick_probe_retract
37 A_pick_ready_to_home
→ 사람의 도움을 요청하거나 최대 한 번 재시도
```

한 짝만 들린 경우:

```text
검증된 비대칭 실패 recovery가 있을 때만:
33 A_restore_after_pick_failure
13 A_retract_clear
14 A_clear_to_home

그렇지 않으면:
operator_required
```

Slot B에는 대응하는 B 모션을 사용한다.

### 16.4 모션 metadata manifest

실제 trajectory는 pcm/SD 카드에 있지만 manifest는 Git에서 관리한다. 실제 로봇에 무엇이 적재되어 있는지에 대한 최종 권위는 항상 현재의 `phorce list` 결과다.

```json
{
  "motion_id": 2,
  "name": "intake_probe_15mm",
  "start_anchor": "I0_INTAKE_READY",
  "end_anchor": "I1_INTAKE_PROBED",
  "payload_before": "none",
  "payload_after": "none",
  "safe_to_pause": true,
  "low_energy_end": false,
  "expected_duration_s": null,
  "preconditions": [
    "two_shoes_detected",
    "intake_alignment_valid",
    "all_required_axes_valid",
    "no_motion_busy"
  ],
  "feedback_to_record": [
    "position_rad",
    "velocity_rad_s",
    "current_a",
    "dob_a",
    "temp_c"
  ],
  "success_rule": {
    "type": "probe_signature",
    "thresholds": "TBD_FROM_CLEAN_TRIALS"
  },
  "failure_motion_id": 3,
  "notes": "Short, low-speed taught motion. Never replace with one long insertion."
}
```

전류나 disturbance threshold를 미리 지어내지 않는다.

- 정상 정렬 probe 10회 기록
- 의도적으로 잘못 정렬한 probe 10회 기록
- 각 조건과 축에 대해 평균·최댓값·분포를 기록
- 두 조건을 구분하면서 변동 여유가 있는 threshold를 선정

기록 대상에는 position, velocity, motor current, disturbance estimate, temperature, `valid`가 포함된다. 축 값은 `valid=true`일 때만 사용한다. `current_a`와 `dob_a`는 접촉 후보를 만드는 간접 신호이지 직접 측정한 힘이 아니다.

### 16.5 LLM의 역할 경계

정상 보관·회수 sequence는 결정론적으로 유지한다.

LLM이 선택할 수 있는 것:

- 음성 요청과 일치하는 저장 신발 한 쌍
- 해당 신발이 들어 있는 slot
- 모호한 실패 뒤 graph가 허용한 recovery 후보 중 하나 또는 `operator_required`

```json
{
  "pair_id": "P002",
  "description": "red sneakers with white soles",
  "slot_id": "A"
}
```

그 뒤 로컬 graph가 고정된 slot-A retrieval sequence를 실행한다. LLM이 `16 → 25 → 11 → 7`처럼 임의 sequence를 만들게 하지 않는다. 유효 전이는 graph manager가 결정한다.

### 16.6 phorce Studio 녹화 절차

녹화 전에 축 구성과 모든 관절 영점을 확정한다. 나중에 영점을 바꾸면 이미 저장된 모션의 기준도 이동한다.

각 모션에 대해:

1. 메커니즘을 문서화된 시작 anchor에 정확히 놓는다.
2. 팔, peg 간격, 신발, slot guide 설정을 확인한다.
3. 서보를 끄고 teaching을 시작한다.
4. 천천히 부드럽게 움직인다.
5. 문서화된 종료 anchor에서 정확히 끝낸다.
6. 저장 전에 Studio graph/화면 preview를 확인한다.
7. 설명적인 이름과 note를 붙여 SD 카드에 저장한다.
8. 서보를 켜고 안전구역을 확보한 뒤 보수적으로 시험한다. gain을 시험 조정한다면 Studio의 임시 **적용**과 영구 **설정 저장**을 구분하며, 참가자 런타임 API가 speed/gain 인자를 받는다고 해석하지 않는다.
9. 같은 조건에서 최소 10회 반복한다.
10. 측정 duration과 feedback 범위를 manifest에 기록한다.

완성된 모션은 로봇의 SD 카드에 저장되고 참가자 코드는 나중에 ID로 선택한다.

### 16.7 구현 규칙

1kHz 피드백 callback은 최신 valid 상태를 저장하고 현재 모션 log에 sample을 추가하는 일만 한다. 판단과 `play()` 요청은 느린 state-machine loop에서 실행한다. 로봇에는 큐가 없으므로 callback에서 반복 호출하면 `BUSY`로 거절될 수 있다.

```python
def on_feedback(feedback):
    store_latest_valid_feedback(feedback)
    append_to_current_motion_window(feedback)


while True:
    motion_id = graph.next_motion()

    result, feedback_window = play_and_record(motion_id)

    outcome = evaluate_motion(
        motion_id=motion_id,
        result=result,
        feedback_window=feedback_window,
        camera_state=read_camera(),
    )

    graph.transition(outcome)
```

실제 구현에서는 `next_motion()`이 `no_action`/`operator_required`를 반환하는 경우를 처리하고, 호출 전 live catalog, 현재 anchor, payload, precondition, robot status를 검증한다.

### 16.8 권장 최초 녹화 순서와 milestone

처음부터 모든 모션을 녹화하지 않는다.

1. `home_to_intake_ready`
2. `intake_probe_15mm`
3. `intake_probe_retract`
4. `intake_insert_full`
5. `intake_lift_pair`
6. `intake_held_abort_lower`
7. Slot A 보관 모션
8. Slot A 회수 모션
9. Presentation 모션
10. Slot A가 신뢰성 있게 동작한 뒤에만 slot B

첫 완성 milestone:

> 신발 한 쌍, intake 위치 하나, storage slot 하나로 연속 5회의 store-and-retrieve cycle을 성공한다.

그 뒤에만 slot B 모션을 복제·조정한다.

---

## 17. 설계 대화 기록: Arm 미정 상태와 Vision-first 계획 (2026-08-05)

이 절은 코드 작성 전에 나눈 설계 대화의 현재 결론을 압축한 것이다. `확정`, `유력`, `미정`을 구분하며, 추측을 확정 사양처럼 사용하지 않는다.

### 17.1 현재 작업 목표

- 흐트러진 신발을 인식하고 정리하는 로봇 팔 기반 shoe valet을 만든다.
- 신발 한 쌍을 시각적으로 연결하되, 물리 취급은 우선 **한 짝씩 순차 처리**하는 방향이 유력하다.
- 두 신발이 바로 붙어 있어도 첫 MVP에서는 동시 pickup보다 단일 신발 pickup을 우선하는 것이 안전하고 단순하다.
- 로봇 팔의 세부 설계가 미정이므로, arm-independent vision proof of concept를 먼저 개발한다.

### 17.2 Arm과 end effector: 현재 파악된 내용

| 항목 | 현재 답변 | 상태/영향 |
|---|---|---|
| 한 번에 드는 수 | 보통 한 짝. 두 짝이 바로 옆이면 동시 처리 가능성을 생각 중 | **유력:** MVP는 한 짝씩 |
| End effector | 끝부분에 V형 구조 | **확정**, 정확한 작동 원리는 미정 |
| V 간격 | 고정형, 별도 간격 actuator 없음 | **확정** |
| 작업 범위 | 고정된 지정 영역 전체에 팔이 닿을 예정 | 기구 목표는 정해졌으나 모션 API와의 연결 방식은 미정 |
| Pickup 위치 | 지정 영역 바닥 어디든 대상이 있을 수 있음 | Vision 요구사항으로 확정 |
| 신발 정렬/회전 | 기구적으로 가능할 수도 있음 | **미정**, 검증 필요 |
| Storage slot 수·치수 | 결정되지 않음 | **미정** |
| Joint feedback | 각 관절에서 충분한 피드백을 받을 수 있음 | 필드·축별 의미와 유효성은 실제 구성으로 확인 |
| 관절·payload·출력물 한계 | 작업 중 | **미정**, 안전 검증 전 가정 금지 |
| 한 짝만 잘못 걸린 상태 | 답변 미완료 | **미정**, recovery 설계에 필수 |
| 안전하게 pause 가능한 자세 | 결정되지 않음 | **미정**, anchor 설계 전에 필요 |
| 필요한 pickup 정렬 정밀도 | 결정되지 않음 | **미정**, V 구조 시험으로 측정 |

V 구조에 대해 다음을 사진·스케치·CAD와 물리 시험으로 확인해야 한다.

- 신발 입구 안으로 들어가는지, 밑창 아래로 들어가는지, 뒤에서 미는지, 옆면에 wedge되는지
- 들어 올릴 때 신발이 V에서 미끄러지지 않는 유지 원리
- 허용 가능한 신발 폭·높이·재질 범위
- toe/heel 중 어느 방향으로 접근해야 하는지
- 한쪽만 걸림, 비틀림, 걸림 실패 때의 수동·자동 recovery

### 17.3 중요한 시스템 제약: 임의 좌표와 prerecorded motion의 충돌

Camera는 지정 영역의 임의 `(x, y, angle)`에서 신발을 찾을 수 있지만, 참가자 API는 연속 좌표나 관절 목표를 받지 않고 prerecorded `motion_id` 하나만 실행한다. 따라서 vision 좌표를 곧바로 임의 arm trajectory로 바꿀 수 없다.

작은 `3 × 3` 위치 grid에 4개 방향만 두어도 pickup 접근 모션만 36개가 필요해, 총 50개 슬롯 안에서 lift·store·present·recovery까지 담기 어렵다. 위치와 각도의 discretization만으로 전체 바닥 pickup을 해결하는 것은 현재 API에 맞지 않을 가능성이 높다.

검토할 물리적 해법:

1. Arm이 신발을 밀거나 쓸어 **고정 pickup station/funnel**로 보낸 뒤 소수의 검증된 모션으로 잡는다.
2. 몇 개의 기계적으로 정렬되는 pickup bay만 두고 각 bay에 prerecorded transition을 배정한다.
3. 연속 위치 제어가 실제로 공개되는지 확인하되, 현재 문서 기준으로는 사용할 수 있다고 가정하지 않는다.

현재 권장 MVP는 **vision으로 한 짝을 선택 → 고정 station으로 정렬/이송 → 짧은 probe와 feedback 확인 → 단일 신발 lift**다.

### 17.4 Camera와 scene 조건

| 항목 | 현재 답변 | 상태 |
|---|---|---|
| 처리 컴퓨터 | Jetson | **확정**, 정확한 모델/RAM/JetPack 미정 |
| Camera 방향 | 바닥을 향해 수직으로 내려다봄 | **확정** |
| Camera 설치 | 위치가 영구적으로 고정됨 | **확정** |
| 조명 | 안정적 | **확정** |
| 가림 조건 | 신발끼리 닿을 수 있으나 겹치거나 가려지지는 않음 | MVP 조건으로 **확정** |
| 인식 목표 | 같은 신발끼리 pair grouping | **확정** |
| 좌/우 분류 | 가능하면 필요 | **희망 요구사항** |
| Calibration marker | 설치 가능할 수도 있음 | **미정**, 설치 권장 |
| Camera 높이·바닥 면적 | 답변 없음 | **미정** |
| Toe 방향·opening 위치 필요 여부 | 답변 없음 | V pickup 방식 확정 후 최종 결정 |

고정 overhead camera, 안정된 조명, 무가림 조건은 vision POC에 유리하다. 다만 신발이 서로 닿으므로 일반 bounding box보다 **instance segmentation**이 적합하다.

Depth sensor가 없어도 고정된 바닥 평면 위의 위치는 calibration homography로 추정할 수 있다. 그러나 신발 opening의 깊이, V 접촉, 실제 삽입 깊이는 단안 RGB만으로 신뢰성 있게 측정하기 어렵기 때문에 짧은 probe motion과 joint feedback 검증이 필요하다.

### 17.5 Vision 출력 계약 초안

단순 bounding box보다 아래 정보를 목표로 한다.

- 신발별 instance mask
- 바닥 좌표와 image 좌표
- 장축 orientation과 toe 방향
- heel/opening 후보 위치
- left/right 분류
- pair association
- touching/overlapping/visible 상태
- pickup candidate 여부와 confidence

```json
{
  "frame_id": 142,
  "shoes": [
    {
      "shoe_id": "S01",
      "pair_id": "P01",
      "side": "left",
      "floor_xy_cm": [42.3, 18.7],
      "orientation_deg": 128.0,
      "toe_direction_confidence": 0.83,
      "opening_xy_cm": null,
      "visible": true,
      "touching": true,
      "overlapping": false,
      "pickup_candidate": true,
      "confidence": 0.91
    }
  ]
}
```

Pair matching은 색·texture·길이·폭·visual embedding 유사도와 left/right 조합을 사용한다. 공간적 거리는 약한 단서로만 사용한다. 동일하게 생긴 여러 쌍이 있으면 강제로 연결하지 말고 `uncertain_pair`를 반환한다.

### 17.6 Vision proof of concept 단계

```text
Jetson의 고정 webcam frame
          ↓
floor ROI와 camera calibration
          ↓
shoe instance segmentation
          ↓
touching instance 분리
          ↓
center + orientation + toe/heel 추정
          ↓
left/right + pair matching
          ↓
overlay 영상 + 구조화된 JSON
```

개발 순서:

1. Jetson에서 webcam/recorded video를 안정적으로 읽는다.
2. Lens distortion을 보정하고 바닥 ROI를 정한다.
3. 네 개 이상의 알려진 바닥 점으로 pixel→floor homography를 구한다.
4. 신발별 mask, center, 크기, orientation을 구한다.
5. 닿아 있는 두 신발을 별도 instance로 분리한다.
6. 주축의 180° 모호성을 풀어 toe와 heel을 구분한다.
7. left/right를 분류하고 visually matching pair를 연결한다.
8. 결과를 overlay하고 JSON으로 저장한다.
9. 불확실하거나 실패한 frame을 이후 학습용으로 보관한다.

빠른 첫 baseline은 빈 바닥 reference와 현재 frame의 차이를 이용할 수 있다.

```text
empty-floor reference
        ↓ frame difference
foreground mask
        ↓
contour / connected component
        ↓
center, size, orientation
```

이 방식은 고정 camera와 안정된 조명을 활용해 calibration과 좌표 출력을 빠르게 검증할 수 있지만, 닿은 신발을 하나로 합칠 수 있다. 그 다음 버전은 lightweight custom instance-segmentation model을 사용한다.

첫 vision milestone:

> 2~6개의 서로 겹치지 않는 신발이 있는 overhead image에서 각 신발을 분리 표시하고, center와 orientation을 추정하며, 같은 pair 후보를 묶는다.

### 17.7 Calibration 권장안

작업 영역 가장자리 바깥에 좌표가 알려진 정사각형 marker 네 개를 두는 것이 좋다. 이를 통해:

- pixel을 바닥 좌표로 변환
- camera가 움직였는지 감지
- perspective 보정
- 신발 실제 치수 추정
- 재현 가능한 calibration 유지

Marker를 둘 수 없다면 측정된 바닥 모서리 네 점을 수동 지정할 수 있지만 자동 drift 확인은 불가능하다.

### 17.8 구현 전에 추가로 필요한 정보와 자료

- Jetson 정확한 모델, RAM, JetPack/Ubuntu 버전
- Webcam 모델, 지원 resolution/FPS
- Camera의 대략적인 높이
- 지정 작업 영역의 폭과 길이
- 빈 바닥 reference frame 촬영 가능 여부
- 같은 scene 안에서만 pair를 묶으면 되는지, 보관 후에도 identity를 기억해야 하는지
- Toe 방향과 opening 위치가 V pickup에 실제로 필요한지
- Calibration marker 설치 가능 여부
- 실제 설치 높이와 비슷한 위치에서 찍은 대표 overhead image:
  - 빈 바닥
  - 가지런한 한 쌍
  - 흩어진 한 쌍
  - 여러 쌍
  - 서로 닿은 신발
  - 어두운 신발과 어두운 바닥 같은 어려운 조건
