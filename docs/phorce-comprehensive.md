# phorce — Comprehensive Documentation

Combined source documentation: Quick Guide, Tutorial, Manual, SDK API Reference, and Jetson System Guide.

## Contents

- [1. Quick Guide](#quick-guide)

- [2. Tutorial](#tutorial)

- [3. Manual](#manual)

- [4. SDK API Reference](#sdk-api-reference)

- [5. Jetson System Guide](#jetson-system-guide)


<a id="quick-guide"></a>



<!-- 제목을 표로 감싼 이유: PDF 변환기(soffice)가 body 첫 블록 요소를 훼손하는
     버그가 있는데, 표는 안전하게 렌더링된다 -->
<table style="border:none;width:100%"><tbody><tr><td style="border:none;padding:0">
<h1>phorce 퀵 가이드</h1>
</td></tr></tbody></table>
<p class="lead">젯슨을 처음 받은 여러분이 <b>10분 안에 로봇을 한 번 움직여 보는</b> 것까지.
코드는 한 줄도 안 씁니다. 순서대로만 따라오세요.</p>

<div class="rev"><span class="tag">🔧 2026-08-06 정정</span> <b>배포본(인쇄본)과 다른 부분이 있습니다.</b> 아래 본문에서 같은 주황 박스로 표시된 곳이 이번에 바뀐 내용입니다: Wi-Fi 격리 설정(§3) · 시동 명령 주의 3가지(§3-2) · 영점 버튼 후 실제 순서·대기 시간(3초→10초)과 준비 완료 확인법(§4 스텝4) · 재생 중 화면 표시(§4 스텝5) · Ctrl+C 로는 로봇이 멈추지 않음(§4 스텝2·§6) · 안전 표 보강 — E-Stop 복구 절차·거절 원인·버튼2 동작·발열(§6)</div>

<h2>1. 이게 뭔가요? (30초)</h2>
<p>여러분 앞에는 세 가지가 있습니다. 사람 몸에 비유하면 이렇습니다.</p>
<table>
  <tbody><tr><th>이름</th><th>정체</th><th>몸에 비유하면</th></tr>
  <tr><td><b>Jetson</b> (젯슨)</td><td>작은 컴퓨터. 여러분이 코드를 돌리는 곳</td><td>🧠 <b>뇌</b> — 생각하고 명령을 내림</td></tr>
  <tr><td><b>pcm</b></td><td>Jetson 과 모터 사이의 중계기</td><td>🧵 <b>신경</b> — 명령을 전달</td></tr>
  <tr><td><b>phact</b></td><td>관절마다 붙은 모터 장치</td><td>💪 <b>근육</b> — 실제로 움직임</td></tr>
</tbody></table>
<p>여러분은 <b>뇌(Jetson)</b> 에서 일합니다. 세 개를 케이블로 연결하고 뇌에게 "이 동작 해"라고
말하면, 신경(pcm)을 타고 근육(phact)이 움직입니다.</p>

<h2>2. 딱 두 가지만 기억하세요</h2>
<p>이 시스템에서 여러분이 하는 일은 <b>단 두 방향</b>뿐입니다. 어렵게 생각하지 마세요.</p>
<div class="box">
<p class="big">⬆️ 올라오는 것 — 로봇이 지금 어떤지 (1초에 1000번!)</p>
<p>로봇은 관절들의 위치·속도·힘·온도를 <b>1초에 1000번</b> 여러분에게 계속 알려줍니다.
이걸 <code>/phorce/feedback</code> 이라고 부릅니다. 여러분의 <b>눈</b>입니다.
(피드백 칸은 12개지만 현재 로봇에 장착된 관절은 <b>6개</b> — 빈 칸은 구분할 수 있게 표시되어 옵니다.)</p>
<p class="big">⬇️ 내려가는 것 — "몇 번 동작 해줘"</p>
<p>여러분은 <b>미리 저장된 동작</b> 중 하나를 번호(1~50)로 고릅니다. "7번 동작 재생!" 이렇게요.
로봇이 그 동작을 합니다. 여러분의 <b>입</b>입니다.</p>
</div>
<p>즉, <b>로봇 상태를 보고(⬆️) → 몇 번 동작을 할지 정해서 보낸다(⬇️).</b> 이게 전부입니다.
관절 하나하나를 직접 조종하는 게 아니라, <b>이미 만들어둔 동작을 골라 트는</b> 겁니다
(노래방에서 곡 번호 고르는 것과 똑같아요).</p>

<h2>3. 시작 전 확인, 그리고 시동 걸기 (3분)</h2>

<h3>3-1. 확인 세 가지</h3>
<ul>
  <li>젯슨 전원이 켜져 있고, 화면에 로그인 창이 보이나요?</li>
  <li>처음 로그인하면 <b>비밀번호를 새로 정하라</b>고 나옵니다 — 정상입니다. 새 비밀번호를 정하세요.</li>
  <li><b>로봇(pcm·phact) 전원을 먼저 켜세요.</b> 케이블 연결 확인은 터미널에서 한 줄:
<pre><code>cat /sys/class/net/eno1/operstate     # "up" 이 나오면 로봇과 연결된 것</code></pre>
  <code>down</code> 이 나오면 로봇 전원과 eno1 케이블을 확인하세요.</li>
</ul>

<div class="rev"><span class="tag">8/6 정정</span> <b>Wi-Fi 주의 — 전 팀 필수 설정입니다.</b> 같은 네트워크에 다른 팀의 젯슨이 있으면 <b>내 명령이 다른 팀 로봇에 전달될 수 있습니다</b>. 시동 걸기 전에 아래 한 줄을 실행하고, <b>열려 있는 터미널을 전부 껐다가 다시 여세요</b>:
<pre><code>echo 'export ROS_LOCALHOST_ONLY=1' &gt;&gt; ~/.bashrc</code></pre>
적용 확인은 <code>phorce doctor</code> — "server 둘 이상" 경고가 <b>없으면</b> 됩니다.</div>

<h3>3-2. 시동 걸기 — 터미널 2개</h3>
<p>로봇과 대화하려면 여러분의 젯슨에서 <b>두 개의 프로그램</b>이 돌고 있어야 합니다.
터미널을 두 개 열고 하나씩 실행하세요 (<b>켜 둔 채로 두는 겁니다</b> — 닫으면 연결이 끊깁니다):</p>
<pre><code># 터미널 1 — 로봇 통신 담당 (13개 자가검사가 전부 PASS 로 지나가야 정상)
ros2 run agx_phorce_bridge phorce_monitor --ros-args -p nic:=eno1 -p mode:=op_idle -p axes:=auto -p mbx_enabled:=true

# 터미널 2 — 모션 요청 창구
ros2 run agx_motion_slot motion_action_server --ros-args -p backend:=ecat</code></pre>
<div class="rev"><span class="tag">8/6 정정</span> <b>이 두 명령에 대해 세 가지만 지켜 주세요.</b>
<ul>
  <li><b>명령은 위에 적힌 그대로</b> 입력하세요. <code>mbx_enabled:=true</code> 는 필수입니다 — 빠지면 모든 재생이 <code>CONTRACT_NOT_ACTIVE</code> 로 거부됩니다.</li>
  <li><span class="tag">8/7 정정</span> <code>axes:=auto</code> 는 <b>로봇(pcm)에 저장된 모터 구성을 자동으로 읽어 그대로 따라갑니다</b> — 어떤 모터를 꽂았든 명령은 같습니다. 모터 구성을 바꿨다면 <b>phorce Studio 에서 축 설정을 먼저</b> 하세요 (구성은 로봇의 FLASH 에 저장됩니다). 축 설정과 실제 꽂힌 모터가 다르면 로봇이 명령을 받지 않습니다.</li>
  <li>두 터미널 모두 시작 안내를 몇 줄 찍은 뒤 <b>조용해지는 것이 정상</b>입니다 (준비 완료 대기 상태). 준비 확인은 세 번째 터미널에서 <code>phorce doctor</code> 입니다.</li>
  <li>다시 실행할 때는 <b>반드시 기존 터미널을 <code>Ctrl+C</code> 로 끝낸 뒤</b>에 하세요. 터미널 1이나 2를 두 개씩 띄우면 통신이 꼬입니다.</li>
  <li>터미널 로그에 <code>~/arm</code>, <code>~/confirm</code> 같은 서비스 호출 예시가 보여도 <b>운영진 전용</b>입니다 — 절대 따라하지 마세요.</li>
</ul></div>
<div class="warn box"><b>순서 규칙:</b> 반드시 <b>로봇 전원이 먼저</b>, 터미널 1이 그 다음입니다.
로봇을 껐다 켰다면 터미널 1도 <code>Ctrl+C</code> 후 다시 실행하세요 — 로봇 정보를
시작할 때 한 번 읽기 때문입니다.</div>
<p>이제 <b>세 번째 터미널</b>을 열어 아래 4장을 진행합니다.</p>

<h2>4. 10분 따라하기</h2>

<h3><span class="step">1</span>로봇과 대화가 되는지 확인</h3>
<pre><code>phorce doctor</code></pre>
<p>로봇 시스템이 살아있는지 건강검진하는 명령입니다. 초록색 <code>PASS</code> 나 <code>ok</code>
가 주르륵 나오면 통과입니다.</p>
<div class="warn box"><b>안 되면?</b> <code>command not found</code> 가 나오면 로그아웃했다가
다시 로그인해 보세요. 그래도 안 되면 운영진에게 알려주세요.</div>

<h3><span class="step">2</span>로봇 상태가 올라오는지 눈으로 보기</h3>
<pre><code>ros2 topic hz /phorce/feedback</code></pre>
<p><b>1000</b> 근처 숫자가 계속 나오면, 로봇이 1초에 1000번 자기 상태를 보내는 중입니다.
살아있다는 증거예요. (멈추려면 <code>Ctrl + C</code>)</p>
<div class="rev"><span class="tag">8/6 정정</span> 여기서 <code>Ctrl + C</code> 가 멈추는 것은 <b>화면 표시뿐</b>입니다. 미리 알아 두세요: <code>Ctrl+C</code>·터미널 닫기·취소는 <b>로봇을 멈추지 못합니다</b> — 한 번 시작된 동작은 끝까지 갑니다. 로봇을 즉시 세우는 수단은 <b>물리 E-Stop 버튼뿐</b>입니다.</div>

<h3><span class="step">3</span>지금 할 수 있는 동작 목록 보기</h3>
<pre><code>phorce list</code></pre>
<p>재생할 수 있는 동작이 번호와 이름으로 나옵니다. 예: <code>01 손흔들기</code>.
<b>여기 나오는 번호만</b> 재생할 수 있어요.</p>
<div class="tip box"><b>왜 목록이 로봇에 있나요?</b> 이 목록은 젯슨이 아니라 <b>로봇이 실제로
품고 있는 동작</b>입니다. 로봇에 저장 안 된 동작은 목록에 안 뜨고, 재생도 안 됩니다.
<b>목록에 뜨면 = 쏠 수 있다</b> 로 기억하세요.</div>

<h3><span class="step">4</span>🔘 로봇을 "준비" 상태로 (사람이 버튼)</h3>
<p>전원만 켜졌다고 로봇이 동작을 받지는 않습니다. <b>기체의 영점 버튼(1번)</b>을
<b>0.6초 이상</b> 누르세요.</p>
<ul>
  <li>로봇이 <b>영점 자세</b>를 잡습니다 → <b>움직입니다. 주변을 먼저 확인!</b></li>
  <li><span class="del">약 <b>3초</b> 뒤 서보가 켜지고 <b>동작 받을 준비</b>가 됩니다.</span> <b>누른 시점부터 약 7초 — 총 10초 대기 권장 (아래 정정 박스)</b></li>
</ul>
<div class="rev"><span class="tag">8/6 정정</span> <b>버튼을 누른 뒤 실제 순서는 이렇습니다</b> — 위 불릿처럼 "즉시 움직이고 3초 뒤 서보"가 아닙니다.
<ul>
  <li>버튼 후 약 <b>3초</b>는 <b>안내 방송만</b> 나옵니다. 이 동안 로봇은 <b>움직이지 않습니다</b> — 버튼을 다시 누르거나 로봇에 다가가지 마세요.</li>
  <li>방송이 끝나면 <b>서보가 켜지고</b>, 약 <b>3초</b>에 걸쳐 <b>영점 자세로 이동</b>합니다.</li>
  <li><b>동작 받을 준비</b>까지는 누른 시점부터 약 <b>7초</b> — 여유 있게 <b>총 10초</b> 기다리는 것을 권장합니다.</li>
</ul></div>
<div class="rev"><span class="tag">8/6 정정</span> <b>준비 완료 확인법</b>: 완료를 알리는 방송이나 LED 구분은 따로 없습니다. <code>phorce status</code> 를 실행해 <code>physical idle True</code> 가 보이면 준비 완료입니다.</div>
<div class="stop box"><b>이 버튼을 안 누르면</b> 다음 단계에서 "아직 준비 안 됨
(<code>REJECT_NOT_READY_FOR_MOTION</code>)"으로 거절당합니다. <b>기다려도 안 풀립니다 —
사람이 눌러야</b> 합니다.
<div class="rev"><span class="tag">8/6 정정</span> 단, <b>영점 버튼을 누른 직후 약 7초 동안</b>은 준비가 진행 중이라 같은 거절이 나옵니다 — 이때는 <b>기다리면 풀립니다</b>. 버튼을 다시 누르지 마세요.</div></div>

<h3><span class="step">5</span>🎉 첫 동작 재생 — 코드 0줄</h3>
<pre><code>phorce play 1</code></pre>
<p><b>1번 동작이 실행됩니다.</b> <span class="del">진행률이 표시되고, 끝나면 완료 메시지가 나옵니다.</span>
축하합니다 — 여러분이 방금 로봇을 움직였어요! (다른 번호도 <code>phorce play 3</code> 처럼)</p>
<div class="rev"><span class="tag">8/6 정정</span> 실물에서는 <b>진행률 숫자가 표시되지 않습니다</b>. '수락/실행 상태 확인 중' 한 줄만 보이는 것이 <b>정상</b>입니다 — 멈춘 게 아니니 <code>Ctrl+C</code> 나 재실행을 하지 마시고, <b>'결과: SUCCEEDED'</b> 가 나올 때까지 기다리세요.</div>
<div class="tip box"><b>실수를 겁내지 않아도 됩니다.</b> 없는 번호를 보내거나 준비 안 된
상태에서 보내면 로봇이 <b>스스로 거절</b>하고 이유를 알려 줍니다. 위급할 때는
언제나 <b>물리 E-Stop 버튼</b>입니다.</div>

<h2>5. 버튼으로 하고 싶다면 — 화면(GUI)</h2>
<pre><code>phorce-console</code></pre>
<p>로봇 상태를 <b>그래프로 보고</b>, 동작을 <b>버튼으로 쏘는</b> 화면이 뜹니다. 명령어가
어색하면 이걸 쓰세요. 켜자마자 할 일 하나: 화면 위쪽 <b>대상</b> 칸을 <b>● 실물 로봇</b>으로
바꾸세요 — 그러면 테두리가 <b>빨개지고</b> 버튼이 <b>[실물 전송]</b> 으로 바뀝니다.
(기본값으로 선택된 "시뮬레이터"는 이 행사에서는 쓰지 않습니다 — 그대로 두면 로봇이
안 움직입니다.) 누르기 전에 항상 주변을 확인하세요.</p>

<h2>6. 안전 — 이것만은 꼭</h2>
<div class="rev"><span class="tag">8/6 정정</span> <code>Ctrl+C</code>, 터미널 닫기, 취소 명령은 <b>로봇을 멈추지 못합니다</b> — 이미 시작된 동작은 끝까지 갑니다. <b>즉시 정지 수단은 물리 E-Stop 버튼뿐</b>입니다.</div>
<table>
  <tbody><tr><th>상황</th><th>어떻게</th></tr>
  <tr><td>비상 정지</td><td><b>물리 E-Stop 버튼</b>이 유일합니다. 위급하면 그걸 누르세요 (키보드 아님)
    <div class="rev"><span class="tag">8/6 정정</span> <b>E-Stop 이후 복구 순서</b>: ① E-Stop <b>해제가 먼저</b>입니다 → ② 로봇 전원 재인가 (해제하지 않고 켜면 <b>0.3초 만에 다시 잠깁니다</b>) → ③ 터미널 1 재시작 → ④ 영점 버튼(1번).</div></td></tr>
  <tr><td>실물 전송 전</td><td>항상 <b>로봇 주변에 사람·물건이 없는지</b> 확인</td></tr>
  <tr><td>"준비 안 됨" 거절</td><td>영점 버튼(1번) 0.6초 누르고 <span class="del">3초</span> <b>10초</b> 기다리기
    <div class="rev"><span class="tag">8/6 정정</span> 이 거절(코드 12)의 원인은 세 가지입니다: ① <b>영점 미입력</b> — 버튼 1을 아직 안 누른 경우(가장 흔함) ② <b>E-Stop 래치</b> — E-Stop 이 눌린 채이거나 해제 없이 전원을 켠 경우(위 복구 순서대로) ③ <b>Studio 가 USB 점유 중</b> — 운영진 점검 도구가 연결돼 있는 경우(운영진에게 알려주세요).</div></td></tr>
  <tr><td>"복구 필요" 거절</td><td>2번 버튼으로 파킹 → 다시 영점 버튼
    <div class="rev"><span class="tag">8/6 정정</span> 2번 버튼을 누르면 로봇이 <b>정리 자세로 약 3초 움직입니다</b> — 주변을 먼저 확인하세요. '전원 종료' 방송이 나와도 <b>전원은 꺼지지 않습니다</b>. 이 버튼은 <b>영점을 잡은 뒤(운전 상태)에만</b> 동작합니다.</div></td></tr>
</tbody></table>
<div class="rev"><span class="tag">8/6 정정</span> <b>발열</b>: 이 로봇에는 <b>과열 자동 차단이 없습니다</b>. 안 쓸 때는 2번 버튼으로 파킹해 두시고, 모터가 뜨겁다 싶으면 즉시 E-Stop 을 누르세요. <b>동작 실패 시 복구</b>: 10초 안에 '시스템 레디' 음성이 나오면 <b>버튼 1만</b> 다시 누르고, 음성이 없으면 <b>버튼 2</b>, 에러음이 반복되면 <b>전원 재인가</b>입니다.</div>

<h2>7. 다음은?</h2>
<p>여기까지 왔다면 로봇을 켜고 움직이는 법을 익힌 겁니다. 이제 <b>여러분의 코드</b>로
"로봇을 보고 스스로 판단해 동작을 고르게" 만들 차례입니다.</p>
<ul>
  <li>📘 <b>② 튜토리얼</b> (<code>02-tutorial</code>) — 파이썬/C++ 로 로봇 상태를 읽고, 그에 따라 동작을 고르는 법을 한 단계씩</li>
  <li>📗 <b>③ 매뉴얼</b> (<code>03-manual</code>) — 규칙·안전·용어 참조표</li>
  <li>📙 <b>④ API 레퍼런스</b> (<code>04-api-reference</code>) — 함수·필드 하나하나의 사전. 코딩하다 막히면 여기</li>
  <li>📒 <b>⑤ 시스템 안내</b> (<code>05-system-image</code>) — 이 젯슨이 어떻게 구성돼 있는지 (리눅스에 익숙하다면)</li>
</ul>

<p class="foot">phorce 해커톤 참가자 문서 ① 퀵 가이드 — 함께 보기: ② 튜토리얼 · ③ 매뉴얼 · ④ API 레퍼런스 · ⑤ 시스템 안내</p>






<a id="tutorial"></a>



<h1>phorce 튜토리얼</h1>
<p class="lead">퀵 가이드로 로봇을 한 번 움직여 봤다면, 이제 <b>여러분의 코드</b>가 로봇을
보고 스스로 판단해 동작을 고르게 만듭니다. 쉬운 것부터 한 레슨씩 쌓아 갑니다.
파이썬을 먼저, 그다음 C++ 를 봅니다.</p>

<div class="rev"><span class="tag">🔧 2026-08-06 정정</span> <b>배포본(인쇄본)과 다른 부분이 있습니다.</b> 아래 본문에서 같은 주황 박스로 표시된 곳이 이번에 바뀐 내용입니다: 로봇 스택 필수·내부 인터페이스 직접 호출 금지 안내 추가 · 도입부 "로봇이 스스로 거절" 문구 정정 · 레슨 2/3 예제의 <code>axis[0]</code> 하드코딩을 <code>valid</code> 순회로 정정(이 기체의 살아 있는 축은 1번) · 레슨 3 판단 루프를 엣지 트리거로 수정 + 재생 사이 쉼 추가 · 레슨 3 예외 처리 확대(<code>MotionAborted</code>·<code>PhorceUnavailable</code>·<code>MotionBusy</code> 대응)</div>

<div class="rev"><span class="tag">8/6 정정</span> <b>이 튜토리얼의 모든 코드는 로봇 스택이 켜져 있어야 동작합니다</b> — 퀵 가이드 3절의 터미널 1·2 가 먼저 떠 있어야 합니다. 실행했을 때 "로봇 스택이 떠 있지 않습니다" 오류가 나오면, <b>오류문에 적힌 <code>ros2 run …</code> 명령을 직접 실행하지 말고 운영진을 불러 주세요</b> (스택은 순서와 상태를 아는 사람이 올려야 합니다). 또한 터미널 로그에 보이는 <code>~/arm</code>, <code>~/confirm</code>, <code>/phorce/submit_motion</code> 은 스택 내부용입니다 — <b>절대 직접 호출하지 마세요.</b></div>

<div class="goal box"><b>이 튜토리얼을 끝내면 할 수 있는 것</b><br>
로봇의 관절 상태를 1초에 1000번 받아서, "이런 상황이면 → 이 동작을 재생"하는
여러분만의 규칙(또는 AI)을 코드로 만들 수 있습니다.</div>

<div class="warn box"><b>이 튜토리얼의 코드는 전부 실물 로봇에 붙습니다.</b> <code>play()</code>
가 실행되면 로봇이 실제로 움직입니다 — 실행 전 항상 주변을 확인하세요. 코드 실수는
겁내지 않아도 됩니다: <span class="del">이상한 요청은 로봇이 스스로 거절하고, 위급하면 물리 E-Stop 입니다.</span>
<span class="tag" style="background:#b8430f;color:#fff;font-size:9pt;padding:1px 8px;border-radius:3px;font-weight:bold;">8/6 정정</span>
<b>로봇이 스스로 거절하는 것은 형식이 잘못되었거나 준비가 안 된 요청뿐입니다. 형식이
올바른 요청은 몇 번을 보내든 그대로 실행됩니다</b> — 공간 확보와 반복 자제는 항상
여러분의 몫입니다. 위급하면 물리 E-Stop 입니다.</div>

<h2><span class="lesson">레슨 0</span> &nbsp;준비 운동</h2>
<p>SDK 예제들은 젯슨에 이미 설치돼 있습니다. 어디 있는지 먼저 찾아 둡니다.</p>
<pre><code># 예제 폴더 위치를 EX 라는 이름에 저장 (한 번만)
EX="$(ros2 pkg prefix phorce)/share/phorce/examples"
ls "$EX"
#   01_first_motion.py  02_read_feedback.py  03_feedback_to_motion.py  raw_action.py</code></pre>
<p>예제를 실행하는 법: <code>python3 "$EX/01_first_motion.py" 1</code> (뒤의 <code>1</code> 은 재생할 동작 번호).</p>

<h2><span class="lesson">레슨 1</span> &nbsp;로봇의 눈으로 보기 — 피드백 한 장</h2>
<div class="goal box"><b>목표:</b> 로봇이 보내는 관절 상태를 눈으로 확인한다.</div>
<p>먼저 코드 없이, 로봇이 뭘 보내는지 터미널에서 봅니다.</p>
<pre><code>ros2 topic hz /phorce/feedback          # 1000 근처면 정상 (1초에 1000번)
ros2 topic echo /phorce/feedback --once # 딱 한 장을 펼쳐 보기</code></pre>
<p>한 장 안에는 <b>관절 12개</b> 각각의 정보가 들어 있습니다. 자주 쓰는 것만:</p>
<table>
  <tbody><tr><th>필드</th><th>뜻</th></tr>
  <tr><td><code>position_rad</code></td><td>관절 각도 (라디안). 로봇이 지금 어느 각도인가</td></tr>
  <tr><td><code>velocity_rad_s</code></td><td>관절이 도는 속도</td></tr>
  <tr><td><code>current_a</code></td><td>모터에 흐르는 전류 (힘을 얼마나 쓰는가)</td></tr>
  <tr><td><code>temp_c</code></td><td>모터 온도</td></tr>
  <tr><td><code>valid</code></td><td><b>이 축 데이터를 믿어도 되는가</b> (아주 중요 — 아래 설명)</td></tr>
</tbody></table>
<div class="warn box"><b>꼭 지킬 규칙 하나:</b> 어떤 축 값을 쓰기 전에 그 축의 <code>valid</code>
가 <b>참(true)</b>인지 확인하세요. <code>valid</code> 가 참일 때만 그 숫자가 진짜입니다.
"오래되지 않았으니 괜찮겠지"(<code>!stale</code>)로 대신하면 안 됩니다 — 아직 한 번도
안 온 축은 stale 도 아니거든요. <b>"믿어도 된다"는 증거는 <code>valid</code> 하나뿐</b>입니다.</div>

<h2><span class="lesson">레슨 2</span> &nbsp;파이썬으로 상태 읽기</h2>
<div class="goal box"><b>목표:</b> 코드로 로봇 상태를 받아서 화면에 뿌린다.</div>
<p>가장 쉬운 길은 <code>phorce</code> 라는 준비된 도구(파사드)를 쓰는 겁니다. 복잡한 ROS 설정을
대신 해 줍니다.</p>
<pre><code>import phorce

# connect() 는 로봇(게이트웨이)에 붙는다. with 블록을 나가면 알아서 정리한다.
with phorce.connect() as robot:
    st = robot.status()              # 로봇 상태 요약 한 장 (읽기만 — 명령 안 보냄)
    print("지금 상태:", st.state_name)   # "IDLE" 이면 새 동작을 보내기 좋은 때
    report = robot.doctor()          # 건강검진 (phorce doctor 명령과 같은 판정)
    print("연결 정상?", report.ok)</code></pre>
<p>실행: <code>python3 그파일.py</code>. 상태 이름이 출력되면 성공입니다.
(<code>state_name</code> 이 알려주는 값들 — <code>IDLE</code>·<code>EXECUTING</code>·
<code>RECOVERY_REQUIRED</code> 등 — 은 ④ API 레퍼런스의 Python 탭에 정리돼 있습니다.)</p>

<h3>관절 값 하나하나를 직접 받고 싶다면 (rclpy)</h3>
<p>더 자세한 1kHz 피드백을 직접 구독할 수도 있습니다. 이땐 <b>딱 한 가지 함정</b>이 있어요.</p>
<div class="rev"><span class="tag">8/6 정정</span> 아래 코드의 <code>on_fb</code> 가 바뀌었습니다
(<b>★ 8/6</b> 표시 줄). 배포본은 <code>msg.axis[0]</code> 을 읽었지만, <b>이 장비에서 살아 있는
축은 0번이 아닙니다</b> — 축 구성은 기체마다 다릅니다. 지금 기체는 <code>axis_valid_mask</code>
값이 <b>2</b>, 즉 <b>1번 축(<code>axis[1]</code>)</b> 하나만 살아 있습니다. 어느 기체에서든 돌게
하려면 특정 번호를 박아 두지 말고, <code>axis_valid_mask</code> 또는 각 칸의 <code>valid</code>
필드로 <b>살아 있는 칸을 찾아서</b> 쓰세요 (12칸 중 <code>valid == True</code> 인 칸).</div>
<pre><code>import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data     # ★ 이게 핵심
from agx_msgs.msg import PhorceFeedback

class Watcher(Node):
    def __init__(self):
        super().__init__("watcher")
        # ★ 반드시 qos_profile_sensor_data 로 구독할 것.
        #   그냥 구독하면 1kHz 발행자와 안 맞아서 "한 개도 안 옴" (조용히 침묵).
        self.create_subscription(
            PhorceFeedback, "/phorce/feedback", self.on_fb, qos_profile_sensor_data)

    def on_fb(self, msg):
        for i, ax in enumerate(msg.axis):          # ★ 8/6: 살아 있는 축을 찾아서
            if ax.valid:                           # ★ valid 먼저 확인
                print(f"{i}번 관절 각도: {ax.position_rad:.3f} rad")

rclpy.init(); rclpy.spin(Watcher())</code></pre>
<div class="stop box"><b>가장 흔한 실수:</b> <code>qos_profile_sensor_data</code> 를 빼먹으면
에러도 안 나고 <b>그냥 아무것도 안 옵니다</b>. "왜 조용하지?" 싶으면 이걸 먼저 의심하세요.</div>

<h2><span class="lesson">레슨 3</span> &nbsp;핵심 — 보고 → 판단 → 움직이기</h2>
<div class="goal box"><b>목표:</b> 로봇 상태를 계속 보다가, 조건이 맞으면 동작을 재생한다.
이게 여러분 프로젝트의 뼈대입니다.</div>
<p>여기 <b>가장 중요한 규칙</b>이 있습니다. 두 가지 속도를 <b>섞지 마세요.</b></p>
<table>
  <tbody><tr><th>빠른 일 (1초 1000번)</th><th>느린 일 (1초 2번쯤)</th></tr>
  <tr><td>피드백을 받아서 <b>"최신 상태"만 저장</b>. 판단·전송은 절대 여기서 안 함</td>
      <td>저장된 최신 상태를 보고 <b>판단</b>해서, 필요하면 <b>동작 재생</b></td></tr>
</tbody></table>
<div class="rev"><span class="tag">8/6 정정</span> 아래 코드가 배포본과 세 군데 다릅니다
(<b>★ 8/6</b> 표시 줄).<br>
① 레슨 2 와 같은 정정 — <code>axis[0]</code> 대신 <code>valid</code> 인 칸을 찾아 저장합니다
(이 기체의 살아 있는 축은 1번, <code>axis[1]</code>).<br>
② 판단을 <b>엣지 트리거</b>로 바꿨습니다: 직전 판정을 변수에 기억해 두고, 조건이
<b>거짓→참으로 바뀌는 순간에만</b> <code>play()</code> 를 1회 부릅니다. 배포본처럼 "조건이
참인 동안" 매 루프마다 재생하면 <b>쉼 없이 반복 재생돼 모터가 과열됩니다 — 이 로봇에는
과열 자동 차단이 없습니다.</b> 재생과 재생 사이에는 몇 초라도 쉼을 두세요.<br>
③ 예외 처리를 넓혔습니다 — 아래 "거절을 다루는 법"의 정정 박스를 함께 보세요.</div>
<pre><code>import threading, time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
import phorce
from agx_msgs.msg import PhorceFeedback

latest = {"pos": None}                   # 빠른 콜백이 최신값만 여기 저장

class Observer(Node):                    # 레슨 2 후반과 똑같은 1kHz 구독
    def __init__(self):
        super().__init__("observer")
        self.create_subscription(
            PhorceFeedback, "/phorce/feedback", self.on_fb, qos_profile_sensor_data)
    def on_fb(self, msg):                # 1kHz 로 불림 — 저장만!
        for ax in msg.axis:              # ★ 8/6: 살아 있는(valid) 칸을 찾아 저장
            if ax.valid:
                latest["pos"] = ax.position_rad
                break

rclpy.init()
threading.Thread(target=rclpy.spin, args=(Observer(),), daemon=True).start()
# ↑ 관측은 뒤에서 계속 돌게 둔다 — play() 가 기다리는 동안에도 멈추지 않게

was_high = False                         # ★ 8/6: 직전 판정을 기억 (엣지 트리거)
with phorce.connect() as robot:
    while True:                          # 느린 판단 루프 (0.5초마다)
        time.sleep(0.5)
        p = latest["pos"]
        if p is None:
            continue
        # ── 여기가 여러분의 "머리" ── 규칙이든 AI든 자유
        is_high = p &gt; 0.5                # 예: 살아 있는 관절이 많이 꺾였으면
        if is_high and not was_high:     # ★ 8/6: 거짓→참으로 "바뀌는 순간"에만 1회
            try:
                robot.play(2)            # 2번 동작 재생 (끝날 때까지 기다림)
                time.sleep(3.0)          # ★ 8/6: 재생 사이 쉼 — 모터를 쉬게 한다
            except phorce.MotionBusy:
                print("아직 바쁨 — 다음 루프에 다시")   # ★ 8/6: pass 로 삼키지 말 것
            except phorce.MotionRejected as e:
                print(e.detail)          # 사람 조치 필요 (영점 버튼 등)
                break                    # 계속 돌아 봐야 거절만 쌓임 — 루프 중단
            except phorce.MotionAborted as e:       # ★ 8/6: 재생 중 중단됨
                print(e.detail)
                break                    # 원인을 확인하기 전에는 재시도 금지
            except phorce.PhorceUnavailable:        # ★ 8/6: 스택과 연결이 끊김
                print("로봇 스택 연결 끊김 — 운영진을 불러 주세요")
                break                    # 직접 재기동하지 말 것
        was_high = is_high               # ★ 8/6: 이번 판정을 다음 루프를 위해 기억</code></pre>
<div class="stop box"><b>왜 1kHz 콜백에서 <code>play()</code> 를 부르면 안 되나요?</b>
로봇은 한 번에 동작 하나만 받습니다(대기줄 없음). 1초에 1000번 <code>play</code> 를 부르면
거의 다 "바쁨(BUSY)"으로 버려집니다. <b>판단·전송은 느린 루프에서</b> 하세요.</div>
<div class="tip box"><b>완성 예제:</b> <code>python3 "$EX/03_feedback_to_motion.py"</code> 가
정확히 이 구조입니다. 이 파일을 복사해서 여러분 규칙만 바꾸면 프로젝트가 시작됩니다.</div>
<div class="box"><b>Ctrl+C 로 멈출 때 메시지가 요란해도 정상입니다.</b> 위의 짧은 코드는
종료 처리를 생략해서, 끝낼 때 스레드 관련 경고가 몇 줄 쏟아질 수 있습니다 — 오류가
아닙니다. 깔끔하게 끝나는 종료 처리가 궁금하면 완성 예제 03 의 뒷부분을 보세요.</div>

<h3>거절을 다루는 법</h3>
<p><code>play()</code> 는 상황에 따라 거절될 수 있습니다. 세 가지만 구분하면 됩니다.</p>
<table>
  <tbody><tr><th>예외</th><th>뜻</th><th>대응</th></tr>
  <tr><td><code>MotionBusy</code></td><td>지금 다른 동작 중</td><td><b>기다리면 풀림.</b> 다음 루프에 다시 시도</td></tr>
  <tr><td><code>MotionRejected</code></td><td>준비 안 됨 / 복구 필요 등</td><td><b>사람이 개입.</b> 영점 버튼 또는 복구 버튼</td></tr>
  <tr><td><code>MotionAborted</code></td><td>재생 중 중단됨</td><td>메시지의 복구 절차를 따름</td></tr>
</tbody></table>
<div class="rev"><span class="tag">8/6 정정</span> 위 코드 뼈대의 예외 처리가 배포본보다
넓어졌습니다. 여러분 코드에도 똑같이 적용하세요.<br>
· <b><code>MotionBusy</code> 를 <code>pass</code> 로 조용히 삼키지 마세요</b> — 한 줄이라도
출력해서 바쁨이 눈에 보이게 하세요. 정상적으로는 앞 동작이 끝나면 풀립니다.
<b>같은 바쁨이 20~30초 이상 계속되면</b> 정상이 아닙니다 — 루프를 멈추고 운영진을 불러 주세요.<br>
· <b><code>MotionAborted</code></b>(재생 중 중단)는 <code>e.detail</code> 을 출력하고
<code>break</code> — 원인을 확인하기 전에는 재시도하지 마세요.<br>
· <b><code>PhorceUnavailable</code></b> 은 로봇 스택과의 연결이 끊겼다는 뜻입니다 —
<b>스택을 직접 재기동하지 말고 운영진을 불러 주세요.</b></div>

<h2><span class="lesson">레슨 4</span> &nbsp;C++ 로도 (원한다면)</h2>
<div class="goal box"><b>목표:</b> 같은 일을 C++ 로. 실시간 성능이 필요할 때.</div>
<p>C++ 에서는 <code>phorce_cpp::motion_client</code> 를 씁니다. <code>CMakeLists.txt</code> 에:</p>
<pre><code>find_package(phorce_cpp REQUIRED)
target_link_libraries(내프로그램 phorce_cpp::motion_client)</code></pre>
<pre><code>#include "phorce_cpp/motion_client.hpp"

auto client = phorce::MotionClient::attach(node, phorce::Target::robot());
auto op  = client-&gt;play_async(7);       // 7번 동작 요청 (기다리지 않음)
auto fut = op-&gt;result();

// 타이머/루프 안에서 논블로킹으로 확인 (콜백 안에서 fut.get() 로 막지 말 것)
if (fut.wait_for(std::chrono::milliseconds(0)) == std::future_status::ready) {
    auto r = fut.get();
    if (r.ok()) { /* 성공 */ }
    else if (r.busy()) { /* 바쁨 — 나중에 다시 */ }
    else if (r.needs_operator()) { /* 사람이 버튼 눌러야 */ }
}</code></pre>
<p>실행 예제: <code>ros2 run phorce_cpp phorce_example_01_first_motion 1</code>
(<code>_02_read_feedback</code>, <code>_03_feedback_to_motion</code> 도 있음).</p>
<div class="warn box"><b>재빌드하면 권한이 사라집니다.</b> C++ 프로그램을 <code>colcon build</code>
로 다시 빌드하면 EtherCAT 권한(setcap)이 날아갑니다. 저수준 프로그램을 직접 돌린다면
<code>sudo agr-setcap-ethercat &lt;실행파일&gt;</code> 를 다시 실행하세요. (모션 슬롯 API만 쓰면
해당 없음 — 권한은 게이트웨이가 가짐)</div>

<h2><span class="lesson">레슨 5</span> &nbsp;내 프로젝트로 확장하기</h2>
<p>이제 재료가 다 모였습니다. 아이디어 몇 개:</p>
<ul>
  <li><b>규칙 기반:</b> "관절이 X 이상 꺾이면 인사 동작" 처럼 if 문으로 반응하는 로봇</li>
  <li><b>센서 연동:</b> 여러분이 붙인 센서/카메라 값에 따라 다른 동작을 고르기</li>
  <li><b>순서 재생:</b> 조건에 따라 여러 동작을 이어서 (단, 한 번에 하나씩, 이전 게 끝나면 다음)</li>
  <li><b>AI 판단:</b> 피드백을 입력으로 받는 모델이 "몇 번 동작"을 출력하게</li>
</ul>
<p>핵심은 항상 같습니다: <b>피드백을 보고(⬆️) → 판단 → 동작 번호를 보낸다(⬇️).</b></p>

<div class="goal box"><b>막히면?</b> 운영진에게 이 두 줄의 결과를 그대로 보여주세요:<br>
<code>phorce doctor --json</code> 과 <code>phorce list --json</code></div>

<p class="foot">phorce 해커톤 참가자 문서 ② 튜토리얼 — 함께 보기: ① 퀵 가이드 · ③ 매뉴얼(규칙·안전) ·
<b>④ API 레퍼런스</b>(함수·필드 사전 — 코딩하다 막히면 여기) · ⑤ 시스템 안내</p>






<a id="manual"></a>



<h1>phorce 매뉴얼</h1>
<p class="lead">참가자가 쓰는 명령·API·인터페이스의 체계적 참조. 개념 설명은 퀵 가이드,
따라하기는 튜토리얼을 보세요. 이 문서는 "정확히 뭐가 있고 어떻게 부르나"의 사전입니다.</p>

<div class="rev"><span class="tag">🔧 2026-08-06 정정</span> <b>배포본(인쇄본)과 다른 부분이 있습니다.</b> 아래 본문에서 같은 주황 박스로 표시된 곳이 이번에 바뀐 내용입니다: §9 거절 코드 표의 대응 절차 정정(코드 12·13·5·6·11) · §9 아래 '중단됨(error=번호)' 사유표 신설 · §10 안전 감시자 설명 재서술 + 발열 주의 추가 · §11 error=17 재전송 지시 정정 · §12 운영자 전용 호출 금지 추가</div>

<div class="toc">
<b>차례</b> &nbsp; 1. 시스템 개요 · 2. CLI · 3. GUI · 4. Python API · 5. C++ API ·
6. ROS 2 인터페이스 · 7. 피드백 필드 · 8. 모션 슬롯 계약 · 9. 거절 코드 ·
10. 안전 · 11. 흔한 실수 · 12. 참가자 API 가 아닌 것 · 13. 용어집
</div>

<h2>1. 시스템 개요</h2>
<p><b>Jetson</b>(젯슨, 여러분의 컴퓨터) — <b>pcm</b>(중계기) — <b>phact</b>(관절 모터 — 와이어 12축 중 6축 장착).
참가자가 만지는 표면은 <b>두 방향</b>뿐입니다.</p>
<ul>
  <li><b>⬆️ 피드백:</b> 로봇이 12축 상태를 <b>1kHz</b>(1초 1000번)로 올려보냄 (<code>/phorce/feedback</code>)</li>
  <li><b>⬇️ 모션 재생:</b> 참가자는 <b>모션 ID(1~50) 하나</b>를 보냄 → 미리 저장된 동작을 로봇이 재생</li>
</ul>
<p>모션 궤적은 행사 전 <b>phorce Studio</b>로 만들어 로봇(pcm)에 저장됩니다. 참가자 코드는
관절을 직접 제어하지 않고 <b>재생할 동작 번호만</b> 고릅니다.</p>

<h2>2. CLI 레퍼런스 — <code>phorce</code></h2>
<p>파이썬으로 만든 명령줄 도구. 서브커맨드는 <b>4개</b>입니다.</p>
<table>
  <tbody><tr><th>명령</th><th>하는 일</th><th>기본 타임아웃</th></tr>
  <tr><td><code>phorce doctor</code></td><td>게이트웨이·카탈로그·상태 진단 한 장</td><td>2초</td></tr>
  <tr><td><code>phorce list</code></td><td>재생 가능한 모션 목록 (정본 = 로봇 적재 슬롯)</td><td>5초</td></tr>
  <tr><td><code>phorce play &lt;id&gt;</code></td><td>모션 하나 재생, 완료까지 대기 (진행률 표시)</td><td>30초</td></tr>
  <tr><td><code>phorce status</code></td><td>모션 슬롯 상태 한 장 (읽기 전용)</td><td>2초</td></tr>
</tbody></table>
<p><b>공통 플래그</b> (모든 명령): <code>--target</code>(기본 <code>robot</code> = 실물 — 그대로 두면 됨),
<code>--namespace</code>, <code>--domain-id</code>, <code>--timeout &lt;초&gt;</code>, <code>--json</code>(기계 판독용).</p>
<p><b>종료 코드</b> (스크립트에서 유용):</p>
<table>
  <tbody><tr><th>코드</th><th>뜻</th><th>코드</th><th>뜻</th></tr>
  <tr><td><code>0</code></td><td>성공</td><td><code>3</code></td><td>게이트웨이 없음</td></tr>
  <tr><td><code>1</code></td><td>거부/실패/준비안됨</td><td><code>4</code></td><td>타임아웃</td></tr>
  <tr><td><code>2</code></td><td>사용법 오류</td><td><code>5</code></td><td>BUSY (요청 폐기, 큐 없음)</td></tr>
  <tr><td colspan="2"></td><td><code>130</code></td><td>사용자 취소(Ctrl+C)</td></tr>
</tbody></table>
<div class="tip box"><code>phorce list</code> 의 목록은 젯슨 파일이 아니라 <b>로봇이 실제 적재한
슬롯</b>(0x4202 비트맵)입니다. 목록에 뜨면 재생 가능, 안 뜨면 불가.</div>

<h2>3. GUI — <code>phorce-console</code></h2>
<p>관측·전송용 샘플 화면 (PyQt5). 실행: <code>phorce-console</code>. 별도 API 가 아니라
참가자와 <b>똑같은 모션 액션</b>을 부르는 ROS 2 노드입니다.</p>
<ul>
  <li>12축 위치/속도/전류/온도 관측, 시계열 그래프(동시 8채널), 신선도·E-Stop·EtherCAT 상태</li>
  <li>모션 슬롯 버튼 전송 — <b>대상 칸을 ● 실물 로봇으로 바꿔 사용</b> (기본값 "시뮬레이터"는
      이 행사에서 쓰지 않음). 실물 선택 시 테두리 빨강 + 버튼 <b>[실물 전송]</b> + 경고문 (3중 동시)</li>
  <li>자동 반복 재생 기능 없음. <code>python3-pyqtgraph</code> 없으면 그래프만 비활성(관측·전송은 동작)</li>
</ul>

<h2>4. Python API</h2>
<p>여기는 요약입니다 — <b>전체 시그니처·클래스별 메서드·필드 사전은
<a href="http://10.249.182.121:8080/docs/04-api-reference.html#py">04-api-reference 의 Python 탭</a></b>을 보세요.</p>
<h3>4-1. <code>phorce</code> 파사드 (권장, 가장 쉬움)</h3>
<pre><code>import phorce
with phorce.connect() as robot:          # 기본 target=robot(실물) — 그대로 쓰면 됨
    result = robot.play(1)               # 완료까지 블로킹
    print(result.ok)                     # ★ 속성(attribute)입니다. ok() 아님
    for m in robot.motions():            # 카탈로그 순회
        print(m.id, m.name)
    handle = robot.play_async(2, on_feedback=cb)   # 비동기
    handle.wait(timeout=30)</code></pre>
<p><b>공개 심볼:</b> <code>connect</code>, <code>doctor</code>, <code>Robot</code>, <code>Target</code>,
<code>Motions</code>, <code>Motion</code>, <code>Catalog</code>, <code>Feedback</code>, <code>Status</code>,
<code>PlayHandle</code>, <code>PlayResult</code>.<br>
<b>예외:</b> <code>PhorceError</code>(최상위), <code>PhorceUnavailable</code>, <code>MotionBusy</code>,
<code>MotionRejected</code>, <code>MotionAborted</code>.<br>
<b>상수:</b> <code>MIN_MOTION_ID</code>(1), <code>MAX_MOTION_ID</code>(50), <code>NO_MOTION_ID</code>(0).</p>
<div class="tip box">거절/실패는 조용히 지나가지 않고 <b>예외</b>로 옵니다. <code>try/except</code> 로
<code>MotionBusy</code>(기다림) / <code>MotionRejected</code>(사람 개입)만 구분하면 충분합니다.</div>

<h3>4-2. 표준 rclpy (직접 구독)</h3>
<pre><code>from rclpy.qos import qos_profile_sensor_data     # ★ 필수
from agx_msgs.msg import PhorceFeedback
node.create_subscription(PhorceFeedback, "/phorce/feedback", cb, qos_profile_sensor_data)</code></pre>
<div class="stop box"><b>QoS 함정:</b> <code>/phorce/feedback</code> 는 반드시
<code>qos_profile_sensor_data</code>(best-effort)로 구독. 기본 reliable 로 하면 에러 없이
<b>한 개도 안 옵니다.</b></div>

<h2>5. C++ API — <code>phorce_cpp::motion_client</code></h2>
<p>여기는 요약입니다 — <b>전체 시그니처와 구조체 필드는
<a href="http://10.249.182.121:8080/docs/04-api-reference.html#cpp">04-api-reference 의 C++ 탭</a></b>을 보세요.</p>
<pre><code>find_package(phorce_cpp REQUIRED)
target_link_libraries(x phorce_cpp::motion_client)   // 공개 의존: rclcpp, rclcpp_action, agx_msgs</code></pre>
<table>
  <tbody><tr><th>타입 / 메서드</th><th>설명</th></tr>
  <tr><td><code>MotionClient::attach(node, Target)</code></td><td>클라이언트 생성. 스스로 spin 안 함(executor 는 호출자 몫)</td></tr>
  <tr><td><code>play_async(id, cb={})</code></td><td>동작 요청 → <code>shared_ptr&lt;PlayOperation&gt;</code></td></tr>
  <tr><td><code>motions_async()</code></td><td>카탈로그 조회 → future</td></tr>
  <tr><td><code>latest_status()</code>, <code>action_ready()</code>, <code>wait_for_action_server()</code></td><td>상태·준비 확인</td></tr>
  <tr><td><code>PlayOperation::result()</code></td><td><code>shared_future&lt;PlayResult&gt;</code></td></tr>
  <tr><td><code>PlayOperation::cancel()</code></td><td>취소 (E-Stop 아님 — 실물에선 거부될 수 있음)</td></tr>
  <tr><td><code>PlayResult::ok()</code></td><td>성공 여부</td></tr>
  <tr><td><code>PlayResult::busy()</code></td><td><b>큐 가득참(코드 5)일 때만 참</b> → 재시도 루프 조건</td></tr>
  <tr><td><code>PlayResult::needs_operator()</code></td><td>코드 12·13 (사람이 버튼)</td></tr>
  <tr><td><code>Target::robot()</code></td><td>대상 선택 (기본값 — 실물)</td></tr>
</tbody></table>
<p><b>상수:</b> <code>kMinMotionId=1</code>, <code>kMaxMotionId=50</code>, <code>kNoMotionId=0</code>,
<code>kMaxSequenceLength=1</code>, <code>kStateFreshLimitMs=1500</code>.</p>
<div class="warn box">콜백 안에서 <code>future.get()</code> 으로 블로킹하지 마세요(자기 자신을 굶깁니다).
타이머/루프에서 <code>wait_for(0ms)</code> 로 논블로킹 확인하세요.</div>

<h2>6. ROS 2 인터페이스</h2>
<table>
  <tbody><tr><th>이름</th><th>종류 / 타입</th><th>속도·QoS</th><th>용도</th></tr>
  <tr><td><code>/phorce/feedback</code></td><td>topic · <code>PhorceFeedback</code></td><td>1kHz · sensor_data</td><td>⬆️ 12축 실시간 상태 (참가자 입력)</td></tr>
  <tr><td><code>/phorce/status</code></td><td>topic · <code>PhorceStatus</code></td><td>10Hz · reliable</td><td>모드·지터·카운터 요약</td></tr>
  <tr><td><code>/phorce/motion_window</code></td><td>topic · <code>MotionWindowStatus</code></td><td>2Hz · latched</td><td>적재 슬롯 비트맵·busy 등</td></tr>
  <tr><td><code>…/play_motion_sequence</code></td><td>action · <code>PlayMotionSequence</code></td><td>—</td><td>⬇️ <b>참가자 유일 구동 API</b></td></tr>
  <tr><td><code>…/motion_slot_state</code></td><td>topic · <code>MotionSlotState</code></td><td>—</td><td>모션 슬롯 상태 (읽기 전용, 폴링→발사 금지)</td></tr>
  <tr><td><code>~/list_motion_slots</code></td><td>service · <code>ListMotionSlots</code></td><td>—</td><td>카탈로그 조회</td></tr>
</tbody></table>
<p>Raw 액션 호출 (파사드 없이, CLI 와 동일 경로):</p>
<pre><code>ros2 action send_goal /motion_action_server/play_motion_sequence \
  agx_msgs/action/PlayMotionSequence "{motion_ids: [1], stop_on_error: true}" -f</code></pre>

<h2>7. 피드백 필드 (<code>PhorceFeedback</code> / <code>AxisFeedback[12]</code>)</h2>
<p><b>프레임당:</b> <code>stamp</code>, <code>wkc</code>, <code>tx_cycle_seq</code>, <code>axis_valid_mask</code>,
<code>axis_stale_mask</code>, <code>axis_oper_mask</code>, <code>axis_fault_mask</code>, <code>am_rx_age_ms</code>, <code>status_flags</code>, <code>axis[12]</code>.</p>
<table>
  <tbody><tr><th>축당 필드</th><th>뜻</th></tr>
  <tr><td><code>position_rad</code> / <code>velocity_rad_s</code></td><td>관절 각도(rad) / 각속도(rad/s)</td></tr>
  <tr><td><code>current_a</code> / <code>dob_a</code></td><td>모터 전류(A) / 외란 추정(A)</td></tr>
  <tr><td><code>bus_v</code> / <code>temp_c</code></td><td>전압(V) / 온도(°C)</td></tr>
  <tr><td><code>kp_echo</code> / <code>kd_echo</code></td><td>적용 중 게인 되울림 (<code>kp</code>=A/rad, <code>kd</code>=A/(rad/s) — 전류 도메인)</td></tr>
  <tr><td><code>valid</code></td><td><b>이 축을 믿어도 되는 유일한 양(+)의 증거.</b> <code>!stale</code> 로 대체 금지</td></tr>
  <tr><td><code>oper</code> / <code>stale</code> / <code>fault</code></td><td>운전중 / 오래됨 / 결함</td></tr>
</tbody></table>

<h2>8. 모션 슬롯 계약</h2>
<ul>
  <li>재생 가능 ID: <b><code>1..50</code></b></li>
  <li><code>0</code> = no-motion sentinel — <b><code>play(0)</code> 금지</b></li>
  <li><code>motion_00.csv</code> = 템플릿, 카탈로그·재생에서 제외</li>
  <li>요청 하나당 ID 하나 (<code>max_sequence_length = 1</code>)</li>
  <li>카탈로그 정본 = <b>로봇(pcm)</b> 이 적재한 슬롯. 젯슨 파일 아님</li>
</ul>

<h2>9. 거절 코드 (<code>PlayMotionSequence</code> reject_reason)</h2>
<table>
  <tbody><tr><th>코드</th><th>이름</th><th>대응</th></tr>
  <tr><td>5</td><td>QUEUE_FULL / BUSY</td><td><b>기다리면 풀림.</b> 재시도 루프는 이 코드에서만
    <div class="rev"><span class="tag">8/6 정정</span> 단, <b>1분 이상 지속되면</b> 기다려도 안 풀리는
    상태일 수 있습니다. 10초 안에 '시스템 레디' 음성이 나오는지 확인하세요 — 음성이 있으면
    <b>버튼1만</b> 누르고, 없으면 <b>버튼2</b>를 누르세요(로봇이 약 3초 움직입니다).
    에러음이 반복되면 전원을 다시 인가하세요.</div></td></tr>
  <tr><td>12</td><td>NOT_READY_FOR_MOTION</td><td><b>사람:</b> 영점 버튼(1번) 0.6초 → <span class="del">3초 대기</span> <b>7초 대기(총 10초)</b>
    <div class="rev"><span class="tag">8/6 정정</span> 이 코드의 원인은 세 갈래입니다.
    ㉠ <b>영점 미입력</b> → 버튼1 누르고 10초 기다린 뒤 재시도.
    ㉡ <b>E-Stop 래치</b> → <b>운영진을 부르세요</b>(버튼만으로는 풀리지 않습니다).
    ㉢ <b>phorce Studio(USB) 세션 점유</b> → USB 연결을 해제하세요.</div></td></tr>
  <tr><td>13</td><td>RECOVERY_REQUIRED</td><td><b>사람:</b> 2번 버튼 파킹 → 다시 영점
    <div class="rev"><span class="tag">8/6 정정</span> 버튼2는 <b>영점 후(운전 상태)에만</b> 동작하며,
    누르면 <b>로봇이 정리 자세로 실제로 움직입니다.</b> 누르기 전에 로봇 주변 공간을 확인하세요.</div></td></tr>
  <tr><td>4</td><td>MOTION_ID_NOT_LOADED</td><td><code>phorce list</code> 에 있는 id 사용</td></tr>
  <tr><td>3</td><td>MOTION_ID_RANGE</td><td>1~50 범위로</td></tr>
  <tr><td>6·11</td><td>MASTER_NOT_OP·AXIS_NOT_OPERATIONAL</td><td><span class="del">EtherCAT/축 상태 확인 (배선·전원)</span> <b>운영진을 부르세요</b> — 통전 중 배선·전원은 참가자가 만지지 않습니다</td></tr>
  <tr><td>0·1·2·7·8·9·10</td><td>NONE/EMPTY/TOO_LONG/COMMAND_SOURCE/STATE_STALE/SUPERVISOR_VETO/CONTRACT_NOT_ACTIVE</td><td>요청 형식·상태 문제 — 메시지 detail 참조</td></tr>
</tbody></table>
<div class="rev"><span class="tag">8/6 정정</span> <b>'중단됨(error=번호)' 사유표 (신설).</b>
위의 거절 코드와는 별개로, 요청이 수락되어 <b>실행이 시작된 뒤</b> 실패하면 화면에
<code>error=번호</code>가 붙습니다. 자주 만나는 번호와 참가자 행동:
<table>
  <tbody><tr><th>error=</th><th>로봇이 말하는 사유</th><th>참가자 행동</th></tr>
  <tr><td>8</td><td>로봇이 모션 수신 상태가 아님(영점 미입력·서보 off 등)</td><td>버튼1 영점 → 10초 기다린 뒤 재시도</td></tr>
  <tr><td>15</td><td>PhACT 관절 제어기 고장</td><td><b>재전송 금지</b> — 운영진 호출</td></tr>
  <tr><td>16</td><td>E-Stop이 눌렸음</td><td><b>재전송 금지</b> — 운영진 호출(E-Stop 래치는 버튼만으로 풀리지 않습니다)</td></tr>
  <tr><td>17</td><td>정지 요청으로 중단됨</td><td>'중단됨' 표시여도 <b>로봇이 실제로는 움직이는 중일 수 있습니다</b> — 화면이 아니라 로봇을 눈으로 확인하세요</td></tr>
  <tr><td>20</td><td>phorce Studio가 로봇을 점유 중</td><td>USB 연결 해제 후 재시도</td></tr>
  <tr><td>23</td><td>다른 모션 재생 중(BUSY)</td><td>앞 모션이 끝난 뒤 재시도</td></tr>
</tbody></table>
</div>
<div class="warn box"><b>재시도 루프는 코드 5(BUSY)에서만</b> 돌리세요. 12·13 은 기다려도
안 풀립니다 — 사람이 버튼을 눌러야 합니다.</div>
<p style="font-size:9pt;color:#666">표의 이름은 줄인 표기입니다 — 정식 상수와 Python
<code>.reason</code> 문자열에는 <code>REJECT_</code> 접두사가 붙습니다
(예: <code>REJECT_QUEUE_FULL</code>). 코드에서 비교할 때는 숫자(<code>.code</code>)가 안전합니다.</p>

<h2>10. 안전</h2>
<ul>
  <li><b>비상 정지는 물리 E-Stop 버튼</b> 하나뿐. 코드의 <code>cancel()</code> 은 E-Stop 이 아님</li>
  <li>실물 전송 전 항상 로봇 주변 확인</li>
  <li><span class="del">모든 하행 명령은 게이트웨이의 <b>안전 감시자</b> 6단계(하드veto→신선도→NaN→한계→슬루)를 통과해야 나감</span></li>
  <li><span class="del">참가자 API(모션 슬롯)는 이 감시자를 우회할 수 없음 — 안전하게 설계됨</span></li>
</ul>
<div class="rev"><span class="tag">8/6 정정</span> 위 취소선 두 줄을 바로잡습니다. 6단계 안전 감시자는
참가자가 쓰지 않는 <b>저수준 스트리밍 명령을 검사하는 장치</b>입니다. 여러분이 쓰는 <b>모션 재생은
차단(발사 가능/불가) 검사만 거치며, 일단 시작되면 저장된 궤적이 그대로 실행됩니다.</b>
시스템이 위험한 동작을 걸러 주지 않습니다 — <b>로봇 주변 공간 확보는 항상 사용자 몫</b>입니다.</div>
<div class="rev"><span class="tag">8/6 정정</span> <b>발열 주의 (추가):</b> 과열 자동 차단이 <b>없습니다</b> —
<code>temp_c</code> 온도는 <b>표시만</b> 됩니다. 쉼 없는 반복 재생은 하지 마세요.
<code>temp_c</code> 상승, 발열, 탄내가 느껴지면 <b>즉시 중단하고 E-Stop</b>을 누르세요.</div>

<h2>11. 흔한 실수</h2>
<table>
  <tbody><tr><th>증상</th><th>원인·해결</th></tr>
  <tr><td>doctor 가 NOT READY / "서버 없음"</td><td>스택(터미널 2개)을 안 켰거나 닫음 — ① 퀵 가이드 3-2절 시동 걸기</td></tr>
  <tr><td>모션 목록·상태가 계속 빈 채</td><td>로봇 전원보다 스택을 먼저 켰음 — 터미널 1(monitor) 재시작</td></tr>
  <tr><td>버튼 복구 직후 첫 재생이 "중단됨(error=17)"</td><td>상태 갱신(0.5초 주기)이 따라오기 전 — <span class="del"><b>한 번 더 보내면 됩니다</b></span>
    <div class="rev"><span class="tag">8/6 정정</span> '중단됨' 표시는 로봇 정지를 뜻하지 않습니다 —
    <b>로봇이 실제로 움직이는 중일 수 있습니다.</b> 로봇이 완전히 멈춘 것을 <b>눈으로 확인한
    뒤에만</b> 재전송하세요. 이미 움직였다면 그 모션은 실행된 것입니다.</div></td></tr>
  <tr><td>피드백이 하나도 안 옴(에러도 없음)</td><td>QoS 누락 → <code>qos_profile_sensor_data</code> 로 구독</td></tr>
  <tr><td>거의 다 BUSY 로 거절</td><td>빠른 콜백에서 <code>play()</code> 호출 → 느린 루프로 옮기기 (큐 없음)</td></tr>
  <tr><td>계속 "준비 안 됨"</td><td>영점 버튼(1번) 안 눌림 — 사람이 눌러야</td></tr>
  <tr><td><code>phorce: command not found</code></td><td>재로그인. 그래도 없으면 그 보드 재검수</td></tr>
  <tr><td>C++ 재빌드 후 권한 오류</td><td><code>sudo agr-setcap-ethercat &lt;실행파일&gt;</code> 재실행(저수준만 해당)</td></tr>
  <tr><td>로봇이 안 움직임(에러 없음)</td><td>GUI 대상 칸이 기본값 "시뮬레이터"로 남아 있는 경우가 대부분 — <b>● 실물 로봇</b>으로 변경</td></tr>
</tbody></table>

<h2>12. 참가자 API 가 아닌 것 (의도적 비공개)</h2>
<p>다음은 참가자용이 아닙니다. 이것 없이도 로봇을 충분히 다룰 수 있게 설계됐습니다.</p>
<ul>
  <li>관절 1kHz 직접 스트리밍, raw PDO/SDO 접근</li>
  <li>레시피 4량({목표위치, 피드포워드토크, Kp, Kd}) 저수준 명령 — 내부/벤치 전용</li>
  <li>CSV·P/F/I Vector 편집 — 이것은 행사 전 phorce Studio 의 몫</li>
</ul>
<div class="rev"><span class="tag">8/6 정정</span> <code>~/arm</code>, <code>~/confirm</code>,
<code>/phorce/submit_motion</code> 은 터미널 로그나 <code>ros2 service list</code> 에 보이더라도
<b>절대 직접 호출하지 마세요.</b> 운영자 전용이며, 안전 절차를 우회해 <b>예고 없는 동작</b>이
일어날 수 있습니다.</div>

<h2>13. 용어집</h2>
<table>
  <tbody><tr><td><b>Jetson</b> (젯슨)</td><td>여러분이 코드를 돌리는 컴퓨터(뇌)</td></tr>
  <tr><td><b>pcm</b></td><td>Jetson 과 모터 사이 중계기(신경). EtherCAT 슬레이브 — 모션 슬롯을 적재·재생하는 주체(카탈로그 정본)</td></tr>
  <tr><td><b>phact</b></td><td>관절마다 붙은 모터 장치(근육). 와이어 12축 중 현 기체는 6축 장착</td></tr>
  <tr><td><b>모션 슬롯 / ms_id</b></td><td>미리 저장된 동작 하나와 그 번호(1~50)</td></tr>
  <tr><td><b>피드백</b></td><td><code>/phorce/feedback</code> — 12축 상태를 1kHz 로 올리는 스트림</td></tr>
  <tr><td><b>게이트웨이</b></td><td>참가자 요청을 받아 안전 검사 후 로봇에 전달하는 보호 계층</td></tr>
  <tr><td><b>EtherCAT</b></td><td>Jetson–pcm 을 잇는 산업용 실시간 통신(1kHz)</td></tr>
  <tr><td><b>phorce Studio</b></td><td>행사 전 모션 궤적을 만들어 로봇에 저장하는 도구(참가자 미사용)</td></tr>
  <tr><td><b>영점 버튼</b></td><td>기체의 1번 버튼. 로봇을 모션 수신 상태로 만드는 물리 버튼</td></tr>
</tbody></table>

<p class="foot">phorce 해커톤 참가자 문서 ③ 매뉴얼 — 함께 보기: ① 퀵 가이드 · ② 튜토리얼 ·
④ API 레퍼런스(함수·필드 사전) · ⑤ 시스템 안내</p>






<a id="sdk-api-reference"></a>



<!-- 제목을 표로 감싼 이유: PDF 변환기(soffice)가 body 첫 블록 요소를 훼손하는
     버그가 있는데, 표는 안전하게 렌더링된다 -->
<table style="border:none;width:100%"><tbody><tr><td style="border:none;padding:0">
<h1>phorce SDK — API 레퍼런스</h1>
</td></tr></tbody></table>

<p class="lead">이 문서는 SDK 가 여러분에게 열어 준 <b>모든 창구의 사전</b>입니다.
앞부분(시스템 지도와 공통 규칙)만 읽고, 그 다음부터는 <b>여러분이 쓰는 언어의
탭 하나만</b> 골라 보면 됩니다 — Python 만 쓸 거라면 Python 탭만 보면 충분합니다.</p>

<div class="rev"><span class="tag">🔧 2026-08-06 정정</span> <b>배포본(인쇄본)과 다른 부분이 있습니다.</b> 아래 본문에서 같은 주황 박스로 표시된 곳이 이번에 바뀐 내용입니다: ① 취소(cancel) — 실물 로봇은 취소 요청 자체를 받지 않습니다(§4-5·Python·CLI) ② 진행 소식 Feedback 의 <code>current_motion_id</code>·<code>pvector_index</code> 는 실물에서 고정값(Python·ROS 2 탭) ③ §2 시스템 지도 — 게이트웨이는 과열을 막아 주지 않습니다 ④ §4-3 거절 코드 5·12 의 대응 절차 보강 ⑤ §8 표에 <code>~/arm</code>·<code>~/confirm</code> 등 3항목 추가 ⑥ Status 에 COMPLETED 상태 추가 + 예외에서 <code>TimeoutError</code>·<code>TypeError</code> 는 <code>PhorceError</code> 로 안 잡힘 ⑦ §3 네임스페이스 — 다른 팀 로봇과 그래프가 합쳐질 수 있어 <code>ROS_LOCALHOST_ONLY=1</code> 적용</div>

<h2 id="place">1. 여러분이 서 있는 곳 — 무엇을 만들고, 무엇은 맡기는가</h2>

<p>phorce 시스템에서 Jetson 은 <b>로봇의 두뇌이자 여러분의 개발 컴퓨터</b>입니다.
역할 분담은 이렇게 정해져 있습니다:</p>

<table>
<tbody><tr><th></th><th>누가</th><th>무엇을</th></tr>
<tr><td>🧠 <b>판단</b></td><td><b>여러분의 코드</b></td><td>로봇의 상태를 보고 "언제, 몇 번 모션을 재생할지" 결정 — AI 정책, 제어 로직, 데모 시나리오 전부 여기</td></tr>
<tr><td>⚙️ <b>실행</b></td><td>우리가 만든 시스템</td><td>1초에 1000번(1kHz) 로봇과 통신하며 모션을 실제로 재생하고, 매 순간 안전을 검사</td></tr>
</tbody></table>

<div class="box"><b>제약 조건 — 먼저 알고 시작하세요.</b><br>
① <b>관절을 직접 실시간으로 조종하는 길은 막혀 있습니다.</b> "3번 관절을 0.5초 동안
30도로" 같은 명령을 보내는 API 는 없습니다. 이것은 안전 설계입니다 — 빠른 제어
루프는 검증된 시스템만 만질 수 있습니다.<br>
② 로봇을 움직이는 방법은 <b>모션 번호(1~50) 전송, 단 하나</b>입니다. 로봇에 미리
담겨 있는 모션(동작 파일)을 번호로 골라 재생하는 방식입니다 — 노래방에서 곡 번호를
입력하는 것과 같습니다.<br>
③ 대신 <b>관측은 활짝 열려 있습니다.</b> 모든 관절의 위치·속도·전류·온도가 1초에
1000번 여러분에게 옵니다. 이 데이터로 판단하는 코드가 여러분의 작품입니다.</div>

<h2 id="map">2. 시스템 지도</h2>

<p>여러분의 명령이 로봇까지 내려가는 길(왼쪽 ▼)과, 로봇의 상태가 여러분에게
올라오는 길(오른쪽 ▲)입니다. 초록 = 여러분의 영역, 보라 = SDK, 갈색 = 로봇.</p>

<table class="diagram">
<tbody><tr><td colspan="2" class="dbox d-you" style="border:2px solid #2c8a4a;background:#eaf5ee;border-radius:8px;padding:8px 12px;text-align:center"><b>여러분의 코드</b> — AI 정책 · 제어 로직 · 시나리오<br>
<span style="font-size:9pt">어떤 언어든: 터미널(CLI) · Python · C++ · 화면(GUI) · ROS 2 직접</span></td></tr>
<tr><td class="dchan" style="width:50%">▼ "3번 재생해" (모션 번호)</td>
    <td class="dchan">▲ 관절 상태 1초에 1000번 (피드백)</td></tr>
<tr><td colspan="2" class="dbox d-sdk" style="border:2px solid #5e4b8b;background:#f0edf6;border-radius:8px;padding:8px 12px;text-align:center"><b>SDK 공개 창구</b> (누구나 같은 규칙)<br>
<span style="font-size:9pt">재생 액션 <code>PlayMotionSequence</code> 하나 + 관측 토픽 4개 + 목록 서비스 1개</span></td></tr>
<tr><td class="dchan" colspan="2">▼ ▲</td></tr>
<tr><td colspan="2" class="dbox d-gw" style="border:2px solid #888;background:#f2f2f2;border-radius:8px;padding:8px 12px;text-align:center"><b>게이트웨이</b> — 요청 검증 · 안전 검사 · 1kHz 통신 <span style="font-size:9pt">(SDK 가 운영 — 여러분이 만지지 않음)</span></td></tr>
<tr><td class="dchan" colspan="2">▼ ▲ &nbsp;EtherCAT 케이블 (1kHz)</td></tr>
<tr><td colspan="2" class="dbox d-robot" style="border:2px solid #75552d;background:#faf6ee;border-radius:8px;padding:8px 12px;text-align:center"><b>로봇</b> — <b>pcm</b>(모션 재생과 안전의 최종 결정권자) → <b>phact ×6</b>(관절 모터)</td></tr>
</tbody></table>

<div class="tip"><b>이 그림이 말해 주는 것:</b> 어느 문(언어)으로 들어가도 전부
가운데의 <b>같은 공개 창구</b>로 모입니다. 그래서 CLI 로 되는 일은 Python 으로도,
C++ 로도 똑같이 됩니다. <span class="del">그리고 여러분의 코드에 실수가 있어도 게이트웨이와 pcm 이
이상한 요청을 거절하므로 로봇은 다치지 않습니다.</span>
<div class="rev"><span class="tag">8/6 정정</span> 게이트웨이와 pcm 이 거절해 주는
것은 <b>형식이 틀리거나 상태가 안 맞는 요청뿐</b>입니다. <b>과열을 자동으로 차단해
주지는 않으며</b>, 서보가 켜져 있는 동안에는 가만히 있어도 유지 전류가 계속
흐릅니다. 같은 모션의 반복 재생, 부하를 건 재생, 서보 ON 상태로 오래 방치하는 것은
피하시고, 발열이 느껴지면 <b>E-Stop</b> 을 누르세요.</div></div>

<h2 id="words">3. 자주 나오는 낱말 6개 — 먼저 알아 두면 다 쉬워집니다</h2>

<table>
<tbody><tr><th>낱말</th><th>뜻</th></tr>
<tr><td><b>토픽</b> (topic)</td><td>계속 흘러나오는 방송 채널. 구독하면 새 데이터가 올 때마다 받습니다 (예: 피드백)</td></tr>
<tr><td><b>액션</b> (action)</td><td>"해 줘" 하고 부탁하면 → 진행 소식을 받다가 → 끝나면 결과를 받는 통신. 모션 재생이 액션입니다</td></tr>
<tr><td><b>서비스</b> (service)</td><td>질문 하나, 답 하나 (예: "모션 목록 줘")</td></tr>
<tr><td><b>네임스페이스</b></td><td>이름 앞에 붙는 주소. <span class="del">이 행사 구성에서는 전부 최상위(빈 주소)라 신경 쓸 일 없습니다</span>
<div class="rev"><span class="tag">8/6 정정</span> 전부 최상위(빈 주소)인 것은 맞지만,
그래서 <b>같은 네트워크에 있는 다른 팀 젯슨과 ROS 2 그래프가 자동으로
합쳐집니다</b> — 여러분의 명령이 <b>다른 팀 로봇으로 갈 수 있다</b>는 뜻입니다.
전 팀이 <code>ROS_LOCALHOST_ONLY=1</code> 을 적용합니다(NOTICE-20260806 참조).
재생 전에 <code>phorce doctor</code> 가 중복 server 경고를 내지 않는지 확인하세요.</div></td></tr>
<tr><td><b>블로킹 / 논블로킹</b></td><td>끝날 때까지 기다리는 호출 / 바로 돌아오고 나중에 결과를 받는 호출</td></tr>
<tr><td><b>콜백</b> (callback)</td><td>"데이터가 오면 이 함수를 불러 줘" 하고 맡겨 두는 함수</td></tr>
</tbody></table>

<h2 id="rules">4. 공통 규칙 — 어떤 언어를 쓰든 똑같습니다</h2>

<h3>4-1. 대상(target) — 기본값 그대로 두면 실물 로봇입니다</h3>
<p>CLI·Python·C++ 모두 <b>아무 설정 없이 실행하면 여러분의 실물 로봇에
연결됩니다</b> (기본 대상 <code>robot</code>). 이 행사에서는 이 기본값만 쓰면 되고,
대상을 바꿀 일이 없습니다.</p>
<div class="box">참고: 여기저기서 <b>"시뮬레이터"</b>라는 선택지(<code>sim:이름</code>
표기, GUI 의 대상 칸 등)를 보게 될 텐데, 이 행사에서는 <b>다루지 않습니다</b>.
여러분에게는 실물 로봇이 있으니까요. 시뮬레이터 대상을 고르면 로봇이 안 움직일
뿐입니다 — 실수로 실물이 움직이는 방향의 혼동은 없습니다.</div>

<h3>4-2. 모션 번호</h3>
<ul>
<li>재생할 수 있는 번호는 <b>1 부터 50</b>. 어떤 번호가 실제로 채워져 있는지는
로봇이 알고 있습니다 — <code>phorce list</code> 로 물어보세요.</li>
<li><b>0 은 금지</b>입니다. "모션 없음"을 뜻하는 예약 번호라서 재생 요청에 넣으면
거절됩니다.</li>
<li><b>한 번에 하나만</b> 보냅니다. 두 개를 이어 보내고 싶으면, 첫 번째의
<b>결과를 받은 뒤</b> 두 번째를 보내세요.</li>
</ul>

<h3>4-3. 거절 — 세 가지 경우, 세 가지 대응</h3>
<p>요청이 거절되면 번호와 함께 이유가 옵니다. 딱 세 가지만 기억하세요:</p>
<table>
<tbody><tr><th>코드</th><th>이름</th><th>무슨 상황</th><th>여러분이 할 일</th></tr>
<tr><td>5</td><td><code>QUEUE_FULL</code></td><td>다른 모션이 아직 재생 중</td><td><b>기다렸다가 다시 보내면 됩니다.</b> 재시도해도 되는 유일한 경우
<div class="rev"><span class="tag">8/6 정정</span> 단, <b>1분 이상</b> 계속 5가
나오면 바쁨이 아니라 <b>래치(걸림)를 의심</b>하세요. 복구 절차: 10초 안에
"시스템 레디" 음성이 들리면 <b>버튼1만</b> 누르면 됩니다. 음성이 없으면
<b>버튼2</b>(로봇이 움직이니 주변을 확인하세요). 에러음이 반복되면 <b>전원
재인가</b>.</div></td></tr>
<tr><td>12</td><td><code>NOT_READY_FOR_MOTION</code></td><td>로봇이 모션 받을 준비가 안 됨</td><td>기다려도 안 풀립니다 — 로봇의 <b>영점 버튼(1번)을 0.6초</b> 누르면 <span class="del">약 3초</span> <b>총 10초</b> 뒤 준비됩니다
<div class="rev"><span class="tag">8/6 정정</span> 버튼을 누른 뒤 <b>총 10초</b>까지는
정상적인 대기입니다. 10초가 지나도 계속 12라면 원인은 셋 중 하나입니다:
① <b>영점</b>이 아직 안 잡힘 — 영점 버튼을 다시 ② <b>E-Stop</b> 이 눌려 있음 —
해제 후 다시 ③ <b>Studio</b> 가 명령 창구를 잡고 있음 — Studio 연결을 닫으세요.</div></td></tr>
<tr><td>13</td><td><code>RECOVERY_REQUIRED</code></td><td>직전 동작이 실패해서 복구 필요</td><td><b>2번 버튼(파킹) → 영점 버튼</b> 순서로 사람이 복구합니다</td></tr>
</tbody></table>
<div class="warn"><b>가장 흔한 버그:</b> 12·13 까지 "바쁘니까 재시도"로 처리하면
프로그램이 <b>영원히 재시도만 합니다</b>. "바쁨(busy)"은 코드 5 하나뿐입니다.
전체 거절 코드 목록은 ROS 2 탭에 있습니다.</div>
<p style="font-size:9pt;color:#666">표의 이름은 줄인 표기입니다 — 정식 상수와 Python
<code>.reason</code> 문자열에는 <code>REJECT_</code> 접두사가 붙습니다
(예: <code>REJECT_QUEUE_FULL</code>). 코드에서 비교할 때는 숫자(<code>.code</code>)가 안전합니다.</p>

<h3>4-4. 성공 판정 — <code>ok</code> 하나만 보면 됩니다</h3>
<p>"성공"은 생각보다 깐깐한 개념입니다. 요청이 끝났다고 다 성공이 아니라,
<b>로봇이 이 요청을 진짜 받아서 · 끝까지 재생했고 · 지금 멈춰 있고 · 복구가
필요 없는 상태</b>까지 전부 확인돼야 성공입니다. 이 판정을 SDK 가
<code>ok</code> 하나로 합쳐 줍니다 — 직접 조립하지 마세요.</p>

<h3>4-5. 멈추고 싶을 때</h3>
<div class="stop"><b>즉시 정지는 물리 E-Stop 버튼뿐입니다.</b> <span class="del">코드의
<code>cancel()</code> 은 "아직 시작 안 한 것을 취소해 달라"는 부탁일 뿐이고,
이미 시작된 동작은 끝까지 갑니다. 실물 로봇은 재생 중 취소 기능 자체가 없습니다.</span>
<div class="rev"><span class="tag">8/6 정정</span> 실물 로봇은 <code>cancel()</code>
<b>요청 자체를 받지 않습니다</b>. 아직 시작 전이라도 취소되지 않고, 한 번 수락된
모션은 <b>항상 끝까지 재생</b>됩니다 — 실물에서 <code>CANCELED</code> 결과는 나오지
않습니다. <code>cancel()</code> 을 불렀다고 로봇이 멈춰 있으리라 기대하고
<b>다가가지 마세요</b>. Ctrl+C 도, 터미널을 닫는 것도 이미 시작된 동작을 멈추지
못합니다.</div></div>

<h3>4-6. 데이터를 믿어도 되는가 — 신선도</h3>
<ul>
<li>관절 데이터가 신선하다는 <b>유일한 증거는 <code>valid</code> 필드</b>입니다.
"낡지 않았으니(<code>stale</code> 아님) 신선하겠지"는 틀립니다 — 데이터가 아예
안 온 관절은 둘 다 false 라서요.</li>
<li>모션 상태 정보는 나이가 <b>1500ms 에 도달하면</b>(<code>age_ms ≥ 1500</code>)
"낡음(STALE)"으로 판정됩니다. "로봇이 지금 움직이고 있나?"는 이 값 말고
<b>1kHz 피드백</b>으로 보세요.</li>
</ul>

<h2 id="doors">5. 이제 문을 고르세요</h2>

<p>아래 다섯 부분은 각각 독립된 사용 설명서입니다. <b>화면으로 보고 있다면 아래
버튼으로 원하는 것만 골라 볼 수 있습니다</b> (인쇄물에는 전부 순서대로 실려
있습니다).</p>

<table>
<tbody><tr><th>문</th><th>이럴 때 고르세요</th></tr>
<tr><td><b>CLI</b> — 터미널 명령 <code>phorce</code></td><td>일단 빨리 해 보고 싶다 / 셸 스크립트로 자동화하고 싶다</td></tr>
<tr><td><b>Python</b></td><td>제일 편한 프로그래밍 경로 — 대부분의 참가자에게 추천</td></tr>
<tr><td><b>C++</b></td><td>ROS 2 노드에 통합하거나 성능이 필요할 때</td></tr>
<tr><td><b>ROS 2 직접</b></td><td>SDK 도우미 없이 통신 규약을 직접 쓰고 싶을 때 · 다른 언어를 쓸 때</td></tr>
<tr><td><b>GUI</b> — 화면 <code>phorce-console</code></td><td>코드 없이 그래프를 보고 버튼으로 재생하고 싶을 때</td></tr>
</tbody></table>

<div id="tabbar-slot" class="filled"><button class="tabbtn on" data-key="all">전체 보기</button><button class="tabbtn" data-key="cli">CLI</button><button class="tabbtn" data-key="py">Python</button><button class="tabbtn" data-key="cpp">C++</button><button class="tabbtn" data-key="ros">ROS 2</button><button class="tabbtn" data-key="gui">GUI(화면)</button></div>

<!-- ═══════════════════════ CLI ═══════════════════════ -->
<section class="tabpanel" id="tab-cli">

<h2>CLI — 터미널 명령 <code>phorce</code></h2>

<p>로그인만 하면 바로 쓸 수 있습니다. "서버를 찾지 못했습니다"가 나오면 로봇 스택이
안 켜진 것입니다 — ① 퀵 가이드 3-2절(시동 걸기 — 터미널 2개)부터. 명령은 네 개뿐입니다:</p>

<table>
<tbody><tr><th>명령</th><th>하는 일</th><th>기다리는 시간(기본)</th></tr>
<tr><td><code>phorce doctor</code></td><td>건강검진 — 연결이 되는지, 서버가 살아 있는지, 모션 목록이 준비됐는지 검사</td><td>2초</td></tr>
<tr><td><code>phorce list</code></td><td>재생할 수 있는 모션 번호와 이름 목록</td><td>5초</td></tr>
<tr><td><code>phorce play 번호</code></td><td>그 번호 모션을 재생하고 끝날 때까지 기다림</td><td>30초</td></tr>
<tr><td><code>phorce status</code></td><td>로봇의 모션 상태 한 장 (보기만 — 아무 명령도 안 보냄)</td><td>2초</td></tr>
</tbody></table>

<p><b>모든 명령에 붙일 수 있는 옵션:</b></p>
<table>
<tbody><tr><th>옵션</th><th>뜻</th></tr>
<tr><td><code>--timeout 초</code></td><td>기다리는 시간 바꾸기</td></tr>
<tr><td><code>--json</code></td><td>사람용 출력 대신 기계용 JSON 한 줄 — 스크립트에서 파싱할 때</td></tr>
<tr><td><code>--target</code> / <code>--namespace</code> / <code>--domain-id</code></td><td>대상·주소를 직접 지정 — 이 행사에서는 기본값(실물 로봇)이면 되므로 쓸 일 없음</td></tr>
</tbody></table>

<p><b>끝나고 남기는 번호(exit code)</b> — 스크립트에서 <code>$?</code> 로 확인합니다:</p>
<table>
<tbody><tr><th>번호</th><th>뜻</th></tr>
<tr><td>0</td><td>성공</td></tr>
<tr><td>1</td><td>거절되거나 실패 (화면의 안내문을 읽으세요 — 할 일이 적혀 있습니다)</td></tr>
<tr><td>2</td><td>명령을 잘못 씀</td></tr>
<tr><td>3</td><td>연결할 서버가 없음 (스택이 안 떠 있거나 target 오타)</td></tr>
<tr><td>4</td><td>시간 초과 (<span class="del">재생 취소를 요청하고 끝나지만, <b>로봇 동작은 계속될 수 있음</b></span> <b>8/6 정정: 명령이 기다리기를 멈출 뿐입니다 — 실물 로봇은 취소를 받지 않으므로 시작된 동작은 끝까지 계속됩니다</b>)</td></tr>
<tr><td>5</td><td>바쁨 — 요청은 버려졌으니 기다렸다 다시</td></tr>
<tr><td>130</td><td>Ctrl+C 로 직접 끊음 <b>(8/6 정정: 명령만 끊깁니다 — 이미 시작된 로봇 동작은 Ctrl+C 로도, 터미널을 닫아도 멈추지 않습니다)</b></td></tr>
</tbody></table>

<pre><code># 처음이라면 이 순서로 (전부 실물 로봇 대상)
phorce doctor      # ① 로봇과 대화가 되나 (건강검진)
phorce list        # ② 무슨 모션이 있나
phorce play 1      # ③ 1번 재생! (로봇이 움직입니다 — 주변 확인)

# 스크립트에서 쓸 때
phorce list --json | python3 -m json.tool</code></pre>

</section>

<!-- ═══════════════════════ Python ═══════════════════════ -->
<section class="tabpanel" id="tab-py">

<h2>Python — <code>import phorce</code></h2>

<p>가장 짧은 완전한 프로그램부터 보세요:</p>

<pre><code>import phorce

with phorce.connect() as robot:        # 실물 로봇에 연결 (with 를 쓰면 정리는 자동)
    result = robot.play(1)             # 1번 재생, 끝날 때까지 기다림 — 로봇이 움직입니다!
    print("성공!" if result.ok else result.detail)</code></pre>

<h3>연결 만들기</h3>
<span class="sig">phorce.connect(target="robot", *, timeout=10.0, namespace=None, domain_id=None, require_server=True) → Robot</span>
<p>로봇과의 연결을 만듭니다. timeout 안에 서버가 안 보이면
<code>PhorceUnavailable</code> 예외가 납니다. 여러분이 이미 ROS 2 코드를 쓰고
있어도 안전합니다 — connect 는 자기만의 독립된 통신 문맥을 만들어서 여러분의
<code>rclpy</code> 초기화와 충돌하지 않습니다.</p>

<span class="sig">phorce.doctor(target="robot", *, timeout=2.0, namespace=None, domain_id=None) → DoctorReport</span>
<p>건강검진만 합니다 — 모션은 보내지 않고, 서버가 없어도 동작합니다.
<code>report.ok</code> 와 <code>report.issues</code>(문제 목록)를 보세요.</p>

<h3>Robot — 연결의 중심</h3>
<table>
<tbody><tr><th>메서드</th><th>하는 일</th></tr>
<tr><td><code>play(*ids, stop_on_error=True, timeout=None) → PlayResult</code></td><td><b>블로킹</b> 재생. 번호는 <b>괄호 안에 그냥</b> 넣으세요: <code>robot.play(3)</code>. <code>ms_id=3</code> 처럼 이름 붙여 넣는 형식은 없습니다. timeout 을 주면 그 시간 넘겼을 때 취소를 요청하고 <code>TimeoutError</code> (로봇 동작은 계속될 수 있음)</td></tr>
<tr><td><code>play_async(*ids, stop_on_error=True, on_feedback=None) → PlayHandle</code></td><td><b>논블로킹</b> 재생 — 바로 돌아오고, 진행 소식은 <code>on_feedback</code> 콜백으로</td></tr>
<tr><td><code>status(timeout=2.0) → Status</code></td><td>상태 한 장 읽기 (아무 명령도 안 보냄)</td></tr>
<tr><td><code>motions() → Catalog</code></td><td>모션 목록. <code>for m in robot.motions():</code> 처럼 바로 순회</td></tr>
<tr><td><code>doctor()</code> / <code>close()</code></td><td>진단 / 연결 닫기 (<code>with</code> 문이 자동으로 해 줌)</td></tr>
</tbody></table>

<h3>PlayResult — 재생이 끝나면 받는 것</h3>
<table>
<tbody><tr><th>속성</th><th>뜻</th></tr>
<tr><td><code>ok</code></td><td>성공 여부. <b>괄호 없이</b> <code>result.ok</code> 입니다 (<code>result.ok()</code> 라고 쓰면 에러). 공통 규칙 4-4 의 깐깐한 판정을 다 합친 값</td></tr>
<tr><td><code>status_name</code></td><td><code>"SUCCEEDED"</code> 또는 <code>"CANCELED"</code> <b>둘뿐</b>. 거절·중단은 결과로 돌아오지 않고 아래의 <b>예외로 던져집니다</b> — <code>status_name == "REJECTED"</code> 같은 분기는 절대 실행되지 않는 죽은 코드가 됩니다</td></tr>
<tr><td><code>detail</code></td><td>사람이 읽는 한국어 설명 — 문제가 있으면 <b>할 일</b>이 적혀 있으니 사용자에게 그대로 보여 주세요</td></tr>
<tr><td><code>completed_count</code></td><td>끝까지 재생된 개수 (0 또는 1)</td></tr>
<tr><td>그 외</td><td><code>boot_id</code>·<code>request_id</code>·<code>primary_state</code>·<code>physical_idle</code>·<code>recovery_required</code> 등 로봇 쪽 문맥 — 궁금할 때만 보면 됩니다 (ROS 2 탭에 설명)</td></tr>
</tbody></table>

<h3>예외 — 오류는 타입으로 구분합니다</h3>
<pre><code>PhorceError                  # 뿌리: "phorce 에서 난 문제" 전부
├── PhorceUnavailable        # 연결이 안 됨 (서버 없음/사라짐)
├── MotionRejected           # 거절됨 — .reason(이름), .code(번호), .detail(할 일)
│   └── MotionBusy           # 거절 5(바쁨)만 따로 — 기다리면 풀리니까
└── MotionAborted            # 시작은 했는데 중간에 중단됨</code></pre>
<div class="rev"><span class="tag">8/6 정정</span> 두 가지는 이 나무에 <b>없습니다</b>:
시간 초과는 파이썬 내장 <code>TimeoutError</code>, 정수가 아닌 모션 번호는
<code>TypeError</code> 로 납니다. 둘 다 <code>PhorceError</code> 계열이 아니라서
<code>except phorce.PhorceError</code> 로는 <b>잡히지 않습니다</b> — 필요하면 따로
잡으세요.</div>
<pre><code>try:
    result = robot.play(3)
except phorce.MotionBusy:
    time.sleep(1)                 # 바쁨 — 기다렸다 다시 (이 경우만 재시도!)
except phorce.MotionRejected as e:
    print(e.detail)               # "영점 버튼을 누르세요" 같은 안내 — 사람이 할 차례
except phorce.PhorceUnavailable:
    print("연결 안 됨 — phorce doctor 로 확인하세요")</code></pre>

<h3>PlayHandle — play_async 가 돌려주는 손잡이</h3>
<table>
<tbody><tr><th>멤버</th><th>뜻</th></tr>
<tr><td><code>wait(timeout=None) → PlayResult</code></td><td>끝나기를 기다림. timeout 넘으면 <code>TimeoutError</code> — <b>재생은 계속됩니다</b></td></tr>
<tr><td><code>cancel()</code></td><td><span class="del">취소 부탁 (공통 규칙 4-5 — E-Stop 아님)</span> <b>8/6 정정: 실물 로봇은 이 요청을 받지 않습니다 — 수락된 모션은 항상 완주합니다 (공통 규칙 4-5)</b></td></tr>
<tr><td><code>done</code> / <code>last_feedback</code></td><td>끝났는지 / 마지막으로 받은 진행 소식</td></tr>
</tbody></table>

<h3>Status — 상태 한 장</h3>
<p><code>st = robot.status()</code> 로 받습니다. 제일 유용한 것은
<code>st.state_name</code> 입니다:</p>
<table>
<tbody><tr><th><code>state_name</code></th><th>뜻</th></tr>
<tr><td><code>IDLE</code></td><td>진짜 쉬는 중 — 새 모션을 보내기 좋은 때</td></tr>
<tr><td><div class="rev"><span class="tag">8/6 추가</span><code>COMPLETED</code></div></td><td><div class="rev">직전 모션이 끝난 뒤 <b>다음 재생까지 이 상태가 유지</b>됩니다 — <code>IDLE</code> 로 돌아오지 않는 것이 정상입니다. "쉬는 중" 판정은 state 가 <code>IDLE</code> 또는 <code>COMPLETED</code> 이고 <code>physical_idle</code> 이 True 인지로 하세요</div></td></tr>
<tr><td><code>EXECUTING</code> 등</td><td>재생 진행 중 (지금 보내면 바쁨 거절)</td></tr>
<tr><td><code>RECOVERY_REQUIRED</code></td><td>사람 복구 필요 (거절 13 과 같은 상황)</td></tr>
<tr><td><code>STALE</code></td><td>정보가 낡음 (1.5초 이상) — 판단에 쓰지 마세요</td></tr>
<tr><td><code>CONTRACT_INACTIVE</code> / <code>UNKNOWN</code></td><td>로봇 창구가 안 열렸거나 문맥 미확보 — 이때 다른 필드로 "쉬는 중"을 추측하지 마세요</td></tr>
</tbody></table>

<h3>진행 소식 Feedback (on_feedback 콜백의 인자)</h3>
<p><span class="del"><code>current_motion_id</code>(지금 재생 중인 번호, 0=없음)가 핵심입니다.</span>
<code>pvector_index</code> 는 내부 전송 진행일 뿐이라 <b>"끝났는지" 판정에 쓰면
안 됩니다</b> — 완료는 반드시 결과(<code>wait()</code>)로 확인하세요.</p>
<div class="rev"><span class="tag">8/6 정정</span> <b>실물 로봇에서는
<code>current_motion_id</code> 가 항상 0, <code>pvector_index</code> 는 255 로
옵니다</b> — 두 필드는 시뮬레이터 전용 값입니다. 그러니 0 이 "재생 없음"을 뜻하지
않습니다. 재생 중인지의 판단은 <code>status</code> 의
<code>active_motion_id</code>·<code>primary_state</code>(EXECUTING)와 로봇의
실제 움직임으로 하세요.</div>

<h3>상수 · 환경변수</h3>
<p><code>MIN_MOTION_ID=1</code> · <code>MAX_MOTION_ID=50</code> ·
<code>NO_MOTION_ID=0</code> · <code>MAX_SEQUENCE_LENGTH=1</code> ·
<code>STATE_FRESH_LIMIT_MS=1500</code>. 환경변수(<code>PHORCE_ROBOT_NAMESPACE</code>
등)는 기본값으로 두면 됩니다 — 운영진이 알려 줄 때만 바꾸세요.</p>

<h3>Python 예제 (전부 설치돼 있음)</h3>
<pre><code>EX="$(ros2 pkg prefix phorce)/share/phorce/examples"
python3 "$EX/01_first_motion.py" 1</code></pre>
<div class="warn"><b>예제도 실물 로봇에 연결됩니다</b> — 재생 예제를 실행하면 로봇이
실제로 움직입니다. 실행 전 주변을 확인하세요.</div>
<table>
<tbody><tr><th>파일</th><th>보여주는 것</th></tr>
<tr><td><code>01_first_motion.py</code></td><td>연결 → 재생 → 결과. 최소형</td></tr>
<tr><td><code>02_read_feedback.py</code></td><td>1kHz 피드백 구독 (QoS 설정법 포함)과 <code>valid</code> 판정</td></tr>
<tr><td><code>03_feedback_to_motion.py</code></td><td><b>보고(1kHz) 와 판단(2Hz) 의 속도 분리</b> — 여러분 프로젝트의 뼈대로 추천</td></tr>
<tr><td><code>raw_action.py</code></td><td>SDK 도우미 없이 ROS 2 액션을 직접 부르는 법</td></tr>
</tbody></table>

</section>

<!-- ═══════════════════════ C++ ═══════════════════════ -->
<section class="tabpanel" id="tab-cpp">

<h2>C++ — <code>phorce::MotionClient</code></h2>

<h3>프로젝트에 연결하기</h3>
<pre><code># package.xml 에 한 줄
&lt;depend&gt;phorce_cpp&lt;/depend&gt;

# CMakeLists.txt 에 두 줄
find_package(phorce_cpp REQUIRED)
target_link_libraries(my_node phorce_cpp::motion_client)

// 코드에서
#include "phorce_cpp/motion_client.hpp"
// 패키지 이름은 phorce_cpp 지만, 클래스는 phorce:: 네임스페이스에 있습니다</code></pre>

<div class="warn"><b>제일 중요한 규칙: 이 클라이언트는 스스로 돌지 않습니다.</b>
<code>attach()</code> 는 여러분 노드에 얹힐 뿐이라서, 여러분이
<code>rclcpp::spin(node)</code>(또는 executor)을 돌려야 콜백과 결과가 진행됩니다.
"아무 일도 안 일어나요"의 원인 1위가 spin 누락입니다.</div>

<h3>MotionClient</h3>
<pre><code>auto client = phorce::MotionClient::attach(node);   // 실물 로봇 (기본 대상)

auto op = client-&gt;play_async(3);          // 논블로킹 — 바로 돌아옴
// ... spin 이 돌고 있는 동안 ...
auto fut = op-&gt;result();                  // shared_future&lt;PlayResult&gt;
if (fut.wait_for(std::chrono::milliseconds(0)) == std::future_status::ready) {
    auto r = fut.get();
    if (r.ok()) { /* 성공 */ }
}</code></pre>
<table>
<tbody><tr><th>멤버</th><th>뜻</th></tr>
<tr><td><code>attach(node, Target = Target::robot())</code></td><td>클라이언트 생성 (정적 함수)</td></tr>
<tr><td><code>play_async(번호, 콜백 = {})</code></td><td>재생 시작. 잘못된 번호는 서버에 보내지도 않고 즉시 거절로 완결</td></tr>
<tr><td><code>motions_async()</code></td><td>모션 목록을 future 로</td></tr>
<tr><td><code>latest_status()</code> / <code>set_status_callback(cb)</code></td><td>최신 상태 / 상태 콜백</td></tr>
<tr><td><code>action_ready()</code> / <code>wait_for_action_server()</code></td><td>서버 준비 확인 / 대기</td></tr>
</tbody></table>

<h3>PlayOperation · PlayResult</h3>
<table>
<tbody><tr><th>멤버</th><th>뜻</th></tr>
<tr><td><code>op-&gt;result()</code></td><td>결과 future. <b>콜백 안에서 <code>.get()</code> 으로 기다리면 멈춥니다(데드락)</b> — <code>wait_for(0ms)</code> 로 "됐나?"만 물어보세요</td></tr>
<tr><td><code>op-&gt;cancel()</code> / <code>op-&gt;done()</code></td><td>취소 부탁 (E-Stop 아님) / 끝났는지</td></tr>
<tr><td><code>r.ok()</code></td><td>성공 판정 (C++ 은 <b>메서드</b> — Python 과 달리 괄호 있음)</td></tr>
<tr><td><code>r.busy()</code></td><td>거절 5(바쁨)<b>에서만</b> true — 이때만 재시도</td></tr>
<tr><td><code>r.needs_operator()</code></td><td>거절 12·13 — 기다려도 안 풀리니 <code>detail</code> 을 사용자에게 보여 주세요</td></tr>
<tr><td><code>r.status_name()</code> / <code>r.reject_name()</code></td><td>사람이 읽는 이름</td></tr>
</tbody></table>
<p>상수: <code>kMinMotionId=1</code> · <code>kMaxMotionId=50</code> ·
<code>kNoMotionId=0</code> · <code>kMaxSequenceLength=1</code> ·
<code>kStateFreshLimitMs=1500</code>. <code>Status</code> 구조체는 Python 탭의
Status 와 같은 내용이고 판정 규칙(<code>is_fresh()</code>·<code>state_name()</code>)도
같습니다.</p>

<h3>C++ 예제 (전부 설치돼 있음)</h3>
<table>
<tbody><tr><th>실행 명령</th><th>보여주는 것</th></tr>
<tr><td><code>ros2 run phorce_cpp phorce_example_01_first_motion 1</code></td><td>연결 → 재생 → 결과</td></tr>
<tr><td><code>ros2 run phorce_cpp phorce_example_02_read_feedback</code></td><td>1kHz 피드백 구독</td></tr>
<tr><td><code>ros2 run phorce_cpp phorce_example_03_feedback_to_motion</code></td><td>타이머로 판단 주기 분리 — 콜백에서 안 기다리는 법</td></tr>
<tr><td><code>ros2 run phorce_cpp phorce_cpp_async_example 3</code></td><td>단일 executor 논블로킹 전체 흐름</td></tr>
<tr><td><code>ros2 run phorce_cpp phorce_raw_action_cpp 1</code></td><td>SDK 도우미 없이 액션 직접 호출</td></tr>
</tbody></table>

</section>

<!-- ═══════════════════════ ROS 2 ═══════════════════════ -->
<section class="tabpanel" id="tab-ros">

<h2>ROS 2 직접 — 통신 규약을 그대로 쓰기</h2>

<p>SDK 도우미(Python/C++)는 결국 아래 규약을 대신 불러 주는 것뿐입니다.
다른 언어를 쓰거나 기존 ROS 2 노드에 얹고 싶다면 직접 불러도 됩니다.</p>

<h3>이름 지도</h3>
<table>
<tbody><tr><th>이름</th><th>종류</th><th>타입 (agx_msgs)</th><th>비고</th></tr>
<tr><td><code>/motion_action_server/play_motion_sequence</code></td><td>액션</td><td><code>action/PlayMotionSequence</code></td><td><b>로봇을 움직이는 유일한 창구</b></td></tr>
<tr><td><code>/phorce/feedback</code></td><td>토픽</td><td><code>msg/PhorceFeedback</code></td><td><b>1kHz</b> 관절 관측. 구독 QoS 를 반드시 SensorDataQoS(best-effort)로 — 기본값(reliable)으로 구독하면 <b>에러 없이 0건</b> 옵니다</td></tr>
<tr><td><code>/phorce/status</code></td><td>토픽</td><td><code>msg/PhorceStatus</code></td><td>10Hz 통신 요약 (수신율·모드 등)</td></tr>
<tr><td><code>/phorce/motion_window</code></td><td>토픽</td><td><code>msg/MotionWindowStatus</code></td><td>2Hz, 마지막 값 유지(latched)</td></tr>
<tr><td><code>/motion_action_server/motion_slot_state</code></td><td>토픽</td><td><code>msg/MotionSlotState</code></td><td>모션 상태 (읽기 전용 — 이걸 폴링해서 발사 타이밍을 재는 루프는 금지)</td></tr>
<tr><td><code>/motion_action_server/list_motion_slots</code></td><td>서비스</td><td><code>srv/ListMotionSlots</code></td><td>모션 목록</td></tr>
</tbody></table>

<pre><code># 터미널에서 액션 직접 호출
ros2 action send_goal /motion_action_server/play_motion_sequence \
  agx_msgs/action/PlayMotionSequence "{motion_ids: [1], stop_on_error: true}" -f</code></pre>

<h3>PlayMotionSequence 액션의 세 부분</h3>
<p><b>Goal (보내는 것)</b>: <code>motion_ids</code> — 배열이지만 <b>원소는 정확히
1개</b>만 허용됩니다. <code>stop_on_error</code> 는 형식상 있는 필드라 신경 쓰지
않아도 됩니다.</p>
<p><b>Feedback (진행 소식)</b>: <code>current_motion_id</code>(<span class="del">0=재생 없음</span>),
<code>pvector_index</code>(내부 전송 진행 — 완료 판정 금지, 255=해당 없음) 등.</p>
<div class="rev"><span class="tag">8/6 정정</span> <b>실물 로봇에서는
<code>current_motion_id</code> 가 항상 0, <code>pvector_index</code> 는 255 로
옵니다</b> — 두 필드는 시뮬레이터 전용 값입니다. 0 을 "재생 없음"으로 읽지 마세요.
재생 중인지는 상태(status)의 <code>active_motion_id</code>·<code>primary_state</code>(EXECUTING)와
로봇의 실제 움직임으로 판단하세요.</div>
<p><b>Result (결과)</b>: <code>status</code>(0 SUCCEEDED / 1 REJECTED / 2 ABORTED /
3 CANCELED), <code>completed_count</code>, <code>reject_reason</code>(아래 표),
<code>detail</code>(한국어 안내), 그리고 문맥 필드들.</p>

<h3>거절 코드 전체</h3>
<table>
<tbody><tr><th>코드</th><th>이름</th><th>뜻</th></tr>
<tr><td>0</td><td><code>NONE</code></td><td>거절 아님</td></tr>
<tr><td>1</td><td><code>EMPTY_SEQUENCE</code></td><td>번호를 안 넣음</td></tr>
<tr><td>2</td><td><code>SEQUENCE_TOO_LONG</code></td><td>번호를 2개 이상 넣음</td></tr>
<tr><td>3</td><td><code>MOTION_ID_RANGE</code></td><td>1~50 밖의 번호 (0 포함)</td></tr>
<tr><td>4</td><td><code>MOTION_ID_NOT_LOADED</code></td><td>목록에 없는 번호</td></tr>
<tr><td><b>5</b></td><td><code>QUEUE_FULL</code></td><td><b>다른 모션 재생 중 — 기다리면 풀림</b></td></tr>
<tr><td>6</td><td><code>MASTER_NOT_OP</code></td><td>EtherCAT 버스가 운전(OP) 상태 아님</td></tr>
<tr><td>7</td><td><code>COMMAND_SOURCE</code></td><td>명령 창구가 다른 주인에게 있음</td></tr>
<tr><td>8</td><td><code>STATE_STALE</code></td><td>로봇 상태 정보가 너무 낡음</td></tr>
<tr><td>9</td><td><code>SUPERVISOR_VETO</code></td><td>안전 감시자가 거부</td></tr>
<tr><td>10</td><td><code>CONTRACT_NOT_ACTIVE</code></td><td>모션 창구가 안 열림</td></tr>
<tr><td>11</td><td><code>AXIS_NOT_OPERATIONAL</code></td><td>관절이 운전 상태 아님</td></tr>
<tr><td><b>12</b></td><td><code>NOT_READY_FOR_MOTION</code></td><td><b>영점 버튼 필요</b> (공통 규칙 4-3)</td></tr>
<tr><td><b>13</b></td><td><code>RECOVERY_REQUIRED</code></td><td><b>사람 복구 필요</b> (공통 규칙 4-3)</td></tr>
</tbody></table>
<p style="font-size:9pt;color:#666">정식 상수 이름에는 <code>REJECT_</code> 접두사가
붙습니다 (예: <code>REJECT_QUEUE_FULL</code>) — wire 메시지와 Python <code>.reason</code>
문자열이 그 형태입니다. 코드 비교는 숫자가 안전합니다.</p>

<h3>문맥 필드 — 읽기만 하세요</h3>
<p>결과와 상태에 함께 실리는 <code>boot_id</code>(로봇의 부팅 세대 번호)와
<code>request_id</code>(요청마다 발급되는 번호) 쌍이 "어느 요청 이야기인가"의
신분증입니다. <b>여러분이 만들지 않습니다</b> — 시스템이 발급하고, 여러분은 결과
대조에 읽기만 합니다. <code>physical_idle</code> 은 "로봇이 물리적으로 멈춰 있다"는
로봇의 직접 확인입니다 — 다른 필드에서 멈춤을 추측하지 마세요. 이 대조를
직접 하기 싫으면 Python/C++ 의 <code>ok</code> 를 쓰면 됩니다(그 일을 해 줍니다).</p>

</section>

<!-- ═══════════════════════ GUI ═══════════════════════ -->
<section class="tabpanel" id="tab-gui">

<h2>GUI — 화면 프로그램 <code>phorce-console</code></h2>

<p>코드 없이 로봇을 보고 움직여 볼 수 있는 화면입니다. 터미널에
<code>phorce-console</code> 이라고 치면 켜집니다.</p>

<h3>화면 구성</h3>
<table>
<tbody><tr><th>부분</th><th>무엇</th></tr>
<tr><td>상단 배지</td><td>연결 상태 · 수신 속도(Hz) · 활성 관절 수 · E-Stop 여부가 한눈에</td></tr>
<tr><td>그래프</td><td>관절의 위치·속도·전류·온도 실시간 곡선. 일시정지와 확대 가능</td></tr>
<tr><td>오른쪽 관절 목록</td><td>12개 관절 줄 — 줄을 클릭하면 그 관절이 그래프에 추가됩니다</td></tr>
<tr><td>모션 패널</td><td>모션 번호를 골라 <b>버튼으로 재생</b>. 켜자마자 <b>대상 칸을
"● 실물 로봇"으로 바꾸세요</b> — 테두리가 빨개지고 버튼이 [실물 전송]으로 바뀝니다.
(기본값 "시뮬레이터"는 이 행사에서 쓰지 않습니다 — 그대로 두면 로봇이 안 움직입니다.)</td></tr>
</tbody></table>

<h3>실행 옵션</h3>
<table>
<tbody><tr><th>옵션</th><th>뜻</th></tr>
<tr><td><code>--no-auto-connect</code></td><td>관측만 하고 재생 기능은 끔 (그래프 전용으로 쓸 때)</td></tr>
</tbody></table>

<div class="tip">화면의 재생 버튼에는 보호 장치가 있습니다 — 연타해도 0.5초에 한
번만 나가고, 재생 중에는 새 요청을 만들지 않습니다.</div>

</section>

<!-- ═══════════════════ 공통 (탭 밖) ═══════════════════ -->

<h2 id="data">6. 피드백 데이터 사전 — 1kHz 로 오는 것의 전부</h2>

<p><code>/phorce/feedback</code> 한 건 = 그 순간의 로봇 스냅샷 한 장.
공통 정보 + 관절 12칸(<code>axis[12]</code> — 현재 기체는 6칸 사용)으로 구성됩니다.</p>

<h3>공통 정보</h3>
<table>
<tbody><tr><th>필드</th><th>뜻</th></tr>
<tr><td><code>stamp</code> / <code>recv_monotonic_ns</code></td><td>발행 시각 / <b>취득 시각</b> — 그래프의 x축이나 시간 분석은 꼭 <code>recv_monotonic_ns</code> 로</td></tr>
<tr><td><code>wkc</code></td><td>통신 정상 확인 숫자 (정상 3)</td></tr>
<tr><td><code>tx_cycle_seq</code></td><td>로봇 쪽 사이클 번호 — 건너뛰면 유실이 있었다는 뜻</td></tr>
<tr><td><code>am_rx_seq_echo</code> / <code>relay_seq_echo</code></td><td>로봇이 마지막으로 받아 준 명령 번호의 메아리</td></tr>
<tr><td><code>axis_valid_mask</code> 등 4개 마스크</td><td>12관절의 valid/stale/운전중/결함을 비트로 요약 (bit N = 관절 N)</td></tr>
<tr><td><code>am_rx_age_ms</code></td><td>로봇이 명령을 못 받은 지 얼마나 됐나 (65535 = 오래됨 고정)</td></tr>
<tr><td><code>status_flags</code></td><td>로봇 안전 상태 비트</td></tr>
</tbody></table>

<h3>관절 한 칸 (<code>axis[i]</code>)</h3>
<table>
<tbody><tr><th>필드</th><th>단위</th><th>뜻</th></tr>
<tr><td><code>position_rad</code></td><td>rad</td><td>관절 각도</td></tr>
<tr><td><code>velocity_rad_s</code></td><td>rad/s</td><td>관절 속도</td></tr>
<tr><td><code>current_a</code></td><td>A</td><td>모터 전류 — 힘(토크)에 비례합니다</td></tr>
<tr><td><code>dob_a</code></td><td>A</td><td>바깥에서 미는 힘의 추정값 (외란 관측기)</td></tr>
<tr><td><code>bus_v</code> / <code>temp_c</code></td><td>V / ℃</td><td>전압 / 온도</td></tr>
<tr><td><code>pos_ref_echo_rad</code></td><td>rad</td><td>관절이 실제로 받은 목표 각도의 메아리</td></tr>
<tr><td><code>kp_echo</code> / <code>kd_echo</code></td><td>A/rad · A/(rad/s)</td><td>적용 중인 제어 게인의 메아리</td></tr>
<tr><td><code>abs_valid</code></td><td>0/1</td><td>절대 인코더(전원 꺼도 각도를 기억하는 센서) 정상 여부</td></tr>
<tr><td><code>loop_cnt</code> / <code>axis_seq</code> / <code>age_ms</code></td><td>—</td><td>관절 내부 카운터 / 새 데이터마다 +1 / 데이터 나이(255=한참 됨·미수신)</td></tr>
<tr><td><code>valid</code> · <code>stale</code> · <code>oper</code> · <code>fault</code></td><td>참/거짓</td><td>아래 표</td></tr>
</tbody></table>

<h3>믿어도 되나? — 진리표</h3>
<table>
<tbody><tr><th>상황</th><th><code>valid</code></th><th><code>stale</code></th><th>해석</th></tr>
<tr><td>신선한 데이터 (0~4ms)</td><td>참</td><td>거짓</td><td>믿고 쓰세요</td></tr>
<tr><td>낡은 데이터 (5ms 이상)</td><td>거짓</td><td>참</td><td>판단에 쓰지 마세요</td></tr>
<tr><td>데이터가 아예 없음 (미장착 관절 등)</td><td>거짓</td><td>거짓</td><td><b>"stale 아니니까 괜찮네"가 틀리는 이유가 이 줄입니다</b> — 증거는 <code>valid</code> 하나뿐</td></tr>
</tbody></table>

<h2 id="traps">7. 함정 모음 — 전원이 한 번씩 밟습니다</h2>

<table>
<tbody><tr><th>함정</th><th>증상</th><th>바른 길</th></tr>
<tr><td>피드백 구독 QoS 기본값</td><td>에러도 없이 <b>0건 수신</b></td><td>SensorDataQoS(best-effort)로 구독 — 예제 02 참고</td></tr>
<tr><td>1kHz 콜백 안에서 <code>play()</code></td><td>거절 5 폭탄</td><td>콜백은 <b>저장만</b>, 판단·발사는 느린 주기(예: 2Hz)에서 — 예제 03 참고</td></tr>
<tr><td><code>result.ok()</code> (Python)</td><td>에러 또는 오판</td><td>Python 은 괄호 없이 <code>result.ok</code>, C++ 만 <code>ok()</code></td></tr>
<tr><td>거절 12·13 을 "바쁨" 취급</td><td>무한 재시도</td><td>재시도는 5 만. 12·13 은 사람이 할 차례</td></tr>
<tr><td>C++ 콜백 안에서 <code>future.get()</code></td><td>프로그램 멈춤</td><td><code>wait_for(0ms)</code> 로 물어만 보기</td></tr>
<tr><td><code>pvector_index</code> 로 완료 판정</td><td>영영 안 끝남</td><td>완료는 결과(result)로만</td></tr>
<tr><td><code>!stale</code> 을 신선 증거로</td><td>빈 관절을 신선으로 오판</td><td>증거는 <code>valid</code> 하나뿐 (6장 진리표)</td></tr>
<tr><td>cancel 직후 바로 다음 play</td><td>거절 5</td><td>cancel 은 즉시 정지가 아님 — <b>결과를 받고</b> 다음 요청</td></tr>
</tbody></table>

<h2 id="notyours">8. 보여도 만지면 안 되는 것</h2>

<p>토픽 목록을 뒤지다 보면 아래가 보일 수 있습니다. 시스템 내부용이니 직접
부르지 마세요 — 로봇을 움직이는 공식 창구는 <code>PlayMotionSequence</code> 액션
하나입니다.</p>
<table>
<tbody><tr><th>이름</th><th>정체</th></tr>
<tr><td><code>SubmitMotionRequest</code> 서비스</td><td>시스템 내부의 전달 통로</td></tr>
<tr><td><code>/phorce/aperiodic</code> 토픽</td><td>정비용 진단 이벤트</td></tr>
<tr><td><code>PhorceCommand</code> 메시지</td><td>내부 명령 형식 — 해커톤 범위 밖</td></tr>
<tr><td><code>phorce_monitor</code> 실행 설정</td><td>로봇 통신 담당 프로그램의 설정 (운영자 영역)</td></tr>
<tr><td><div class="rev"><span class="tag">8/6 추가</span><code>~/arm</code> · <code>~/confirm</code> 서비스</div></td><td><div class="rev">시스템 내부의 무장(arming) 절차 — 터미널 로그에 호출법이 보여도 <b>절대 호출하지 마세요</b>. 성공하면 로봇이 예고 없이 움직일 수 있고, 개입 이후 모니터가 안전 정지에 들어가 피드백이 멎을 수 있습니다</div></td></tr>
<tr><td><div class="rev"><span class="tag">8/6 추가</span><code>/phorce/submit_motion</code> 서비스</div></td><td><div class="rev">모션 전달의 내부 통로 — 직접 호출 금지</div></td></tr>
<tr><td><div class="rev"><span class="tag">8/6 추가</span>파라미터 <code>set</code> 서비스</div></td><td><div class="rev">호출해도 효과가 없습니다 — 파라미터는 기동 시 1회만 읽힙니다</div></td></tr>
</tbody></table>

<p class="foot">phorce 해커톤 참가자 문서 ④ API 레퍼런스 —
함께 보기: ① 퀵 가이드 · ② 튜토리얼 · ③ 매뉴얼 · ⑤ 시스템 안내</p>

<script>
(function () {
  var tabs = [
    ["all", "전체 보기"], ["cli", "CLI"], ["py", "Python"],
    ["cpp", "C++"], ["ros", "ROS 2"], ["gui", "GUI(화면)"]
  ];
  var slot = document.getElementById("tabbar-slot");
  if (!slot) return;
  slot.className = "filled";
  var panels = document.querySelectorAll(".tabpanel");
  function show(key) {
    panels.forEach(function (p) {
      p.style.display = (key === "all" || p.id === "tab-" + key) ? "" : "none";
    });
    slot.querySelectorAll(".tabbtn").forEach(function (b) {
      b.classList.toggle("on", b.dataset.key === key);
    });
    // 탭 전환 시 화면을 움직이지 않는다 — 점프가 "느리고 덜컥거리는" 느낌을 준다
  }
  tabs.forEach(function (t) {
    var b = document.createElement("button");
    b.className = "tabbtn"; b.dataset.key = t[0]; b.textContent = t[1];
    b.addEventListener("click", function () { show(t[0]); });
    slot.appendChild(b);
  });
  var hash = (location.hash || "").replace("#", "");
  var keys = tabs.map(function (t) { return t[0]; });
  show(keys.indexOf(hash) >= 0 ? hash : "all");
})();
</script>






<a id="jetson-system-guide"></a>



<!-- 제목을 표로 감싼 이유: PDF 변환기(soffice)가 body 첫 블록 요소를 훼손하는
     버그가 있는데, 표는 안전하게 렌더링된다 -->
<table style="border:none;width:100%"><tbody><tr><td style="border:none;padding:0">
<h1>phorce — 여러분의 Jetson 시스템 안내</h1>
</td></tr></tbody></table>

<p class="lead">여러분이 받은 Jetson(젯슨)이 어떻게 구성되어 있는지를 한 장으로
설명합니다. 그냥 쓰기만 할 거라면 안 읽어도 됩니다 — 전부 미리 연결되어
있습니다. 리눅스를 다뤄 본 분이라면 이 문서로 "커널에 무슨 패치가 됐고, 뭐가 왜
깔려 있는지"를 파악할 수 있습니다.</p>

<div class="rev"><span class="tag">🔧 2026-08-06 정정</span> <b>배포본(인쇄본)과 다른 부분이 있습니다.</b> 아래 본문에서 같은 주황 박스로 표시된 곳이 이번에 바뀐 내용입니다: SSH 비밀번호 로그인 차단과 <code>apt upgrade</code> 금지(§3-3) · 재부팅 후 로봇 통신 프로그램 수동 재시작과 끄고 켜는 순서(§3-4) · 부팅 대기 시간 기준(§3-4) · 내부 서비스 직접 호출 금지(§5-2)</div>

<h2>1. phorce 시스템에서 Jetson 의 역할</h2>

<p>phorce 로봇 시스템은 세 장치의 팀입니다:</p>

<table>
<tbody><tr><th>장치</th><th>몸에 비유하면</th><th>하는 일</th></tr>
<tr><td><b>Jetson</b></td><td>🧠 두뇌</td><td>생각하는 곳 — <b>여러분의 코드가 사는 곳</b>. AI, 판단, 개발 전부 여기</td></tr>
<tr><td><b>pcm</b></td><td>🧵 신경 중추</td><td>모션 재생과 안전의 최종 결정권자. Jetson 의 요청을 받아 관절들을 지휘</td></tr>
<tr><td><b>phact ×6</b></td><td>💪 근육</td><td>관절 하나마다 붙은 모터 장치</td></tr>
</tbody></table>

<div class="box"><b>여러분이 이 위에서 하는 일:</b> 로봇의 상태(1초에 1000번
올라오는 관절 데이터)를 보고, <b>"언제 몇 번 모션을 재생할지" 판단하는 코드</b>
— AI 정책이든 제어 로직이든 — 를 만드는 것입니다.<br><br>
<b>제약 조건:</b> 관절을 직접 실시간으로 조종하는 길은 안전을 위해 막혀
있습니다. 로봇을 움직이는 방법은 <b>모션 번호(1~50) 전송 하나</b>입니다.
이 제약 안에서 작업하시면 됩니다 — 자세한 사용법은 ④ API 레퍼런스에 있습니다.</div>

<h2>2. 시스템 구성도</h2>

<p>초록 = 여러분의 영역, 갈색 = 우리가 설치해 둔 소프트웨어, 붉은색 = 특별히
손본 커널, 회색 = 하드웨어.</p>

<table class="diagram">
<tbody><tr><td class="dbox d-you" style="border:2px solid #2c8a4a;background:#eaf5ee;border-radius:8px;padding:8px 12px;text-align:center"><b>여러분의 작업 공간</b><br>
<span style="font-size:9pt">여러분의 코드 · <code>phorce</code> CLI · Python/C++ 예제 · 화면(<code>phorce-console</code>)</span></td></tr>
<tr><td class="dchan">▼ ▲</td></tr>
<tr><td class="dbox d-sw" style="border:2px solid #75552d;background:#faf6ee;border-radius:8px;padding:8px 12px;text-align:center"><b>phorce SDK</b> (deb 패키지 8개, <code>/opt/ros/humble</code>)<br>
<span style="font-size:9pt">공개 창구 · Python/C++ 클라이언트 · 로봇 통신 프로그램(안전 감시 포함)</span></td></tr>
<tr><td class="dchan">▼ ▲</td></tr>
<tr><td class="dbox d-sw" style="border:2px solid #75552d;background:#faf6ee;border-radius:8px;padding:8px 12px;text-align:center"><b>ROS 2 Humble</b> (로봇 미들웨어 · RViz 등 시각화 포함)</td></tr>
<tr><td class="dchan">▼ ▲</td></tr>
<tr><td class="dbox d-kern" style="border:2px solid #a04545;background:#faf0ee;border-radius:8px;padding:8px 12px;text-align:center"><b>실시간 커널</b> <code>5.15.148-rt-tegra</code> (PREEMPT_RT 패치)<br>
<span style="font-size:9pt">CPU 12개 중 <b>8–11번을 로봇 통신 전용으로 격리</b> — 나머지 0–7번이 여러분 것</span></td></tr>
<tr><td class="dchan">▼ ▲</td></tr>
<tr><td class="dbox d-hw" style="border:2px solid #888;background:#f2f2f2;border-radius:8px;padding:8px 12px;text-align:center"><b>NVIDIA Jetson AGX Orin</b> — Ubuntu 22.04 (L4T 36.4.3 · JetPack 6.2)<br>
<span style="font-size:9pt">CUDA 12.6 · cuDNN 9.3 · TensorRT 10.3 (AI/GPU) · 저장장치 NVMe 1TB</span></td></tr>
<tr><td class="dchan">▼ ▲ &nbsp;유선랜 <code>eno1</code> — 로봇 전용선 (EtherCAT, 1초에 1000번)</td></tr>
<tr><td class="dbox d-hw" style="border:2px solid #888;background:#f2f2f2;border-radius:8px;padding:8px 12px;text-align:center"><b>로봇</b> — pcm → phact ×6</td></tr>
</tbody></table>

<div class="tip"><b>한 문장 요약:</b> 평범한 Ubuntu 22.04 + ROS 2 개발 컴퓨터인데,
<b>커널만 실시간용으로 바꾸고 CPU 4개를 로봇 통신 전용으로 떼어 놓은</b>
시스템입니다. 여러분의 코드는 나머지 8개 코어에서 평범하게 돌면 됩니다.</div>

<h2>3. 핵심 네 가지</h2>

<h3>3-1. 왜 커널이 특별한가 — PREEMPT_RT</h3>
<p>로봇 관절과는 <b>1초에 1000번</b>, 즉 1밀리초에 한 번씩 통신해야 합니다.
보통 커널은 가끔 다른 일을 하느라 수백 마이크로초씩 한눈을 파는데, 로봇
제어에서는 그 한눈이 곧 떨림과 오차가 됩니다. PREEMPT_RT 패치는 커널 내부의
"양보 못 하는 구간"을 거의 없애서, 급한 일이 언제든 CPU 를 바로 차지할 수 있게
만든 것입니다. 확인해 보려면:</p>
<pre><code>uname -r                    # 5.15.148-rt-tegra  ← 끝의 rt 가 실시간 커널 표시
cat /sys/kernel/realtime    # 1</code></pre>

<h3>3-2. CPU 지도 — 8개는 여러분 것, 4개는 로봇 것</h3>
<table>
<tbody><tr><th>코어</th><th>주인</th><th>하는 일</th></tr>
<tr><td><b>0–7</b></td><td>여러분 + 일반 시스템</td><td>여러분의 코드, ROS 2, GUI, 빌드, AI/GPU 작업 — 전부 여기</td></tr>
<tr><td><b>8–11</b></td><td>로봇 통신 (격리)</td><td>1kHz 실시간 루프 전용. 일반 프로세스와 인터럽트가 못 들어오게 커널 수준에서 분리</td></tr>
</tbody></table>
<div class="warn"><b>8–11번 코어에 여러분의 프로세스를 일부러 고정(<code>taskset</code>
등)하지 마세요.</b> 로봇 통신의 전용 차선입니다. 아무것도 안 하면 침범할 일이
없습니다 — 시스템이 알아서 여러분의 프로세스를 0–7번에만 배치합니다.</div>
<p>이 격리 덕분에 로봇 통신의 시간 흔들림(jitter)이 최대 204µs 에서 <b>7µs</b>
수준까지 줄었습니다 — 로봇이 부드럽게 움직이는 비결입니다.</p>

<h3>3-3. 계정과 보드 고유값</h3>
<ul>
<li>계정은 <code>phorce</code> 입니다. <b>처음 로그인할 때 비밀번호를 새로
정하게 되어 있습니다</b> — 모든 보드가 같은 이미지로 만들어졌기 때문에, 첫
로그인에서 보드마다 다른 비밀번호를 갖게 하는 장치입니다.</li>
<li><code>sudo</code> 를 쓸 수 있습니다 — 필요한 패키지는
<code>sudo apt install ...</code> 로 자유롭게 설치하세요.</li>
<li>보드의 신원(machine-id, SSH 지문)은 첫 부팅 때 보드마다 새로 만들어집니다 —
옆 팀 보드와 SSH 지문이 다른 것이 정상입니다.</li>
</ul>

<div class="rev"><span class="tag">8/6 정정</span> <b>SSH 비밀번호 로그인은
꺼져 있습니다.</b> 모든 보드가 같은 초기 비밀번호로 출발하기 때문에 둔
안전장치라서, <b>비밀번호가 맞아도 거부되는 것이 정상</b>입니다. SSH 가 필요하면
보드에서 여러분의 공개키를 <code>~/.ssh/authorized_keys</code> 에 등록해
쓰세요.<br><br>
그리고 <code>sudo apt install</code> 은 자유지만, <b><code>sudo apt upgrade</code>
(<code>full-upgrade</code>·<code>dist-upgrade</code> 포함)는 하지 마세요</b> —
로봇 통신용으로 버전을 고정해 둔 패키지가 함께 올라가 통신이 깨질 수
있습니다.</div>

<h3>3-4. 알아두면 좋은 특성</h3>
<ul>
<li><b>부팅 화면이 한동안 조용합니다.</b> 부팅 설정(<code>video=efifb:off</code>)
때문에 초반 로그가 화면에 안 나옵니다 — 멈춘 게 아니니 기다리세요.
<div class="rev"><span class="tag">8/6 정정</span> 기다림의 기준을 드립니다:
보통 <b>2분</b>, 첫 부팅은 최대 <b>4분</b> 안에 로그인 화면이 나옵니다.
<b>4분이 지나도 조용하면 더 기다리지 말고 운영진을 불러 주세요.</b></div></li>
<li><b>유선랜 포트(<code>eno1</code>)는 로봇 전용선입니다.</b> IP 주소가 없고,
일반 랜선을 꽂아도 인터넷이 되지 않습니다. 인터넷은 Wi-Fi 로 쓰세요.</li>
<li><b>로그인만 하면 <code>phorce</code>·<code>ros2</code> 명령이 바로 됩니다.</b>
로그인할 때 ROS 환경이 자동으로 잡히도록 되어 있어서
<code>source /opt/ros/humble/setup.bash</code> 를 직접 칠 필요가 없습니다.</li>
<li><b>커널·드라이버는 업데이트가 잠겨 있습니다</b>(apt hold). 자동 업데이트가
실시간 커널을 보통 커널로 되돌리는 것을 막기 위해서입니다. 일반 패키지 설치는
전혀 영향받지 않습니다.</li>
</ul>

<div class="rev"><span class="tag">8/6 정정</span> <b>재부팅한 뒤에는 로봇 통신
프로그램을 직접 다시 켜야 합니다.</b> §5-3 의 자동 서비스들과 달리, 로봇 통신
프로그램(퀵 가이드 3절의 터미널 1·2)은 자동으로 시작되지 않습니다. 순서는
언제나 <b>로봇 전원 먼저</b>, 그 다음 터미널 1·2 입니다.</div>

<div class="rev"><span class="tag">8/6 정정</span> <b>젯슨을 재부팅하거나 끄기
전에는 로봇부터 쉬게 해 주세요.</b> 터미널만 꺼져도 로봇 서보는 켜진 채
유지되어 열이 계속 오릅니다. <b>버튼2</b> 로 파킹한 뒤 진행하세요. 외우기 쉽게:
<b>"끌 때는 로봇부터 쉬게, 켤 때는 로봇 전원부터."</b></div>

<h2>4. 커널 부팅 인자 — 격리는 이렇게 구현되어 있습니다</h2>

<p><code>cat /proc/cmdline</code> 에 보이는 실시간 관련 설정입니다. 하나의
세트로 동작합니다:</p>

<table>
<tbody><tr><th>인자</th><th>무엇을 하나</th><th>왜</th></tr>
<tr><td><code>isolcpus=managed_irq,domain,8-11</code></td><td>코어 8–11 을 일반 스케줄러와 인터럽트에서 분리</td><td>로봇 통신 전용 차선 확보</td></tr>
<tr><td><code>nohz_full=8-11</code></td><td>격리 코어의 주기적 타이머 인터럽트(틱) 제거</td><td>1kHz 루프를 건드리는 마지막 방해까지 제거</td></tr>
<tr><td><code>rcu_nocbs=8-11</code> + <code>rcu_nocb_poll</code></td><td>커널 내부 청소 작업을 다른 코어로 위임</td><td>청소 작업이 격리 코어를 깨우지 않게</td></tr>
<tr><td><code>kthread_cpus=0-7</code> · <code>irqaffinity=0-7</code></td><td>커널 스레드와 기본 인터럽트를 0–7 에 묶음</td><td>격리 코어 침범을 원천 차단</td></tr>
<tr><td><code>nohz=on</code></td><td>동적 틱 켜기</td><td>위 세트의 전제 조건</td></tr>
<tr><td><code>video=efifb:off</code></td><td>부팅 초반 화면 출력 끔</td><td>3-4 절 — 부팅이 조용해 보이는 이유</td></tr>
</tbody></table>

<h2>5. Appendix — 설치된 것들과 그 이유</h2>

<p>"이건 왜 깔려 있지?"의 답 모음입니다. 해커톤에서 만나게 될 것만 담았습니다.</p>

<h3>5-1. 기반 소프트웨어</h3>
<table>
<tbody><tr><th>구성요소</th><th>무엇</th><th>왜</th></tr>
<tr><td>실시간 커널</td><td>PREEMPT_RT 패치 리눅스 (3-1 절)</td><td>1kHz 로봇 통신의 시간 보장</td></tr>
<tr><td>Ubuntu 22.04 / L4T 36.4.3</td><td>Jetson 용 기본 운영체제 (JetPack 6.2 세대)</td><td>모든 것의 바탕</td></tr>
<tr><td>CUDA · cuDNN · TensorRT</td><td>GPU 컴퓨팅과 AI 추론 도구 (12.6 / 9.3 / 10.3)</td><td>여러분의 AI 워크로드용</td></tr>
<tr><td>ROS 2 Humble (desktop)</td><td>로봇 미들웨어 + RViz·rqt 시각화</td><td>SDK 와 여러분 코드의 공용 기반</td></tr>
<tr><td>Docker</td><td>컨테이너 실행 도구</td><td>여러분의 추가 소프트웨어 스택을 컨테이너로 돌리고 싶을 때</td></tr>
</tbody></table>

<h3>5-2. phorce SDK (deb 패키지 8개)</h3>
<table>
<tbody><tr><th>패키지</th><th>담긴 것</th></tr>
<tr><td><code>phorce-interfaces</code></td><td>통신 규약 정의 — 메시지·서비스·액션 (모든 언어의 공통 어휘)</td></tr>
<tr><td><code>phorce-cli</code></td><td><code>phorce</code> 터미널 명령 + 로그인 자동 환경</td></tr>
<tr><td><code>phorce-client-py</code></td><td>Python 라이브러리 (<code>import phorce</code>) + 예제</td></tr>
<tr><td><code>phorce-client-cpp</code></td><td>C++ 라이브러리 + 예제</td></tr>
<tr><td><code>phorce-sim</code></td><td>시뮬레이터 (이 행사에서는 사용하지 않음)</td></tr>
<tr><td><code>phorce-console</code></td><td>화면 프로그램 (그래프 · 버튼 재생)</td></tr>
<tr><td><code>phorce-robot-runtime</code></td><td>로봇과 직접 통신하는 프로그램 + 안전 감시자 — <b>로봇 통신선을 만질 수 있는 유일한 패키지</b> (안전 경계)</td></tr>
<tr><td><code>phorce-sdk</code></td><td>위 참가자용 패키지를 한 번에 묶은 메타패키지</td></tr>
</tbody></table>

<div class="rev"><span class="tag">8/6 정정</span> 이 프로그램들의 터미널 로그에는
내부 서비스 이름(<code>~/arm</code>, <code>~/confirm</code>,
<code>/phorce/submit_motion</code>)이 지나갑니다. 이 이름들을
<code>ros2 service call</code> 로 직접 호출하지 마세요 — 안전 감시를 우회하는
내부 통로입니다. 로봇을 움직이는 공식 통로는 <code>phorce</code> CLI 와 Python
라이브러리뿐입니다.</div>

<h3>5-3. 실시간을 지키는 장치들</h3>
<table>
<tbody><tr><th>구성요소</th><th>무엇</th><th>왜</th></tr>
<tr><td><code>jetson-rt-perf.service</code></td><td>부팅마다: 최대 성능 모드 · 클럭 고정 · 격리 코어 절전 금지 · 인터럽트를 0–7 로 정리</td><td>격리 코어가 "잠에서 깨는 지연" 없이 항상 즉응하도록</td></tr>
<tr><td><code>ethercat-nic-opt.service</code></td><td>부팅마다 로봇 전용선(<code>eno1</code>)을 1kHz 통신에 맞게 조율하고, 적용됐는지 되읽어 확인</td><td>패킷이 랜카드에서 뭉치거나 늦지 않게</td></tr>
<tr><td>업데이트 잠금</td><td>커널·드라이버 apt hold + 자동 업데이트 데몬 끔</td><td>자동 업데이트가 실시간 구성을 되돌리지 않게 (3-4 절)</td></tr>
</tbody></table>

<h3>5-4. 연결과 권한</h3>
<table>
<tbody><tr><th>구성요소</th><th>무엇</th><th>왜</th></tr>
<tr><td><code>eno1</code> 로봇 전용</td><td>네트워크 관리자가 이 포트를 건드리지 않게 설정 (IP 없음)</td><td>일반 네트워크 트래픽이 로봇 통신선에 끼어들지 않게</td></tr>
<tr><td>로봇 프로그램의 특별 권한</td><td>로봇 통신 프로그램에만 필요한 최소 권한(raw 네트워크 접근·실시간 우선순위)을 부여하고, 그에 필요한 라이브러리 경로를 시스템에 등록</td><td><code>sudo</code> 없이도 로봇 프로그램이 돌게 — 전체를 root 로 돌리는 것보다 안전</td></tr>
<tr><td>로그인 자동 환경</td><td><code>/etc/profile.d</code> 의 스크립트가 ROS 환경을 자동 적용</td><td>"로그인하면 바로 <code>phorce</code>" (3-4 절)</td></tr>
<tr><td>첫 부팅 자가설정</td><td>보드 신원(machine-id·SSH 키) 생성 + 구성 자가검사</td><td>복제된 보드가 각자 고유해지고, 잘못 구성된 보드는 걸러지게</td></tr>
</tbody></table>

<p class="foot">phorce 해커톤 참가자 문서 ⑤ 시스템 안내 —
함께 보기: ① 퀵 가이드 · ② 튜토리얼 · ③ 매뉴얼 · ④ API 레퍼런스 ·
내 보드 확인: <code>uname -r</code> · <code>dpkg -l 'phorce-*'</code></p>





