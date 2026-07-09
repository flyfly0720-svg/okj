import streamlit as st
import numpy as np
from mpmath import mp
import io
import wave

# ---------- 설정값 ----------
SAMPLE_RATE = 44100
NOTE_DURATION = 0.4      # 음 하나의 길이(초)
C4_FREQ = 261.63         # 중간 도(C4) 주파수

# 숫자 -> (음이름, C4 기준 반음(semitone) 차이)
# 1=도, 2=레, 3=미, 4=파, 5=솔, 6=라, 7=시, 8=높은 도, 9=높은 레
# 0은 1(도) 바로 아래 음으로 이어지도록 낮은 시로 배정
DIGIT_TO_NOTE = {
    0: ("시(낮은)", -1),
    1: ("도", 0),
    2: ("레", 2),
    3: ("미", 4),
    4: ("파", 5),
    5: ("솔", 7),
    6: ("라", 9),
    7: ("시", 11),
    8: ("도(높은)", 12),
    9: ("레(높은)", 14),
}


def get_pi_decimals(n: int) -> str:
    """원주율 소수점 n자리를 문자열로 반환"""
    mp.dps = n + 15  # 오차 방지용 여유 자릿수
    pi_str = mp.nstr(mp.pi, n + 10, strip_zeros=False)
    integer_part, decimal_part = pi_str.split(".")
    return decimal_part[:n]


def digit_to_frequency(digit: int) -> float:
    _, semitone = DIGIT_TO_NOTE[digit]
    return C4_FREQ * (2 ** (semitone / 12))


def make_tone(freq: float, duration: float, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """사인파 톤 생성 (클릭 노이즈 방지용 페이드 인/아웃 포함)"""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave_data = np.sin(2 * np.pi * freq * t)

    fade_len = max(1, int(sample_rate * 0.02))
    envelope = np.ones_like(wave_data)
    envelope[:fade_len] = np.linspace(0, 1, fade_len)
    envelope[-fade_len:] = np.linspace(1, 0, fade_len)

    return wave_data * envelope


def digits_to_wav_bytes(digits: str) -> bytes:
    """숫자열을 이어붙인 오디오 -> WAV 바이트로 변환"""
    audio = np.concatenate([
        make_tone(digit_to_frequency(int(d)), NOTE_DURATION) for d in digits
    ])
    audio = (audio * 32767 * 0.6).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


# ---------- Streamlit UI ----------
st.set_page_config(page_title="원주율 음계 변환기", page_icon="🎵")
st.title("🎵 원주율(π)을 음계로 듣기")
st.write(
    "원주율의 소수점 자리를 음계로 변환합니다. "
    "(1=도, 2=레, 3=미, 4=파, 5=솔, 6=라, 7=시, 8=높은도, 9=높은레, 0=낮은시)"
)

digits_count = st.slider("소수점 몇째 자리까지 들을까요?", min_value=5, max_value=100, value=50)

pi_decimals = get_pi_decimals(digits_count)

st.subheader("π 소수점 값")
st.code(f"3.{pi_decimals}")

note_sequence = [DIGIT_TO_NOTE[int(d)][0] for d in pi_decimals]
st.subheader("음계 시퀀스")
st.write(" - ".join(note_sequence))

if st.button("🎶 소리 생성하기"):
    with st.spinner("소리를 만드는 중..."):
        wav_bytes = digits_to_wav_bytes(pi_decimals)
    st.audio(wav_bytes, format="audio/wav")
    st.download_button(
        label="⬇️ WAV 파일 다운로드",
        data=wav_bytes,
        file_name=f"pi_{digits_count}digits_music.wav",
        mime="audio/wav",
    )

