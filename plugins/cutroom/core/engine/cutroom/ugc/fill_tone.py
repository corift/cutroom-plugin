# fill_tone.py SRC OUT TONE.wav a:b,a:b
# Replace each window (base seconds) with room tone made from TONE.wav, with 15ms fades, then high-pass the
# whole track at 80Hz and write AAC. Use it on the gaps at clip joins to remove Omni "clunks".
import sys, subprocess, wave, numpy as np
def rd(f):
    w=wave.open(f); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(float)/32768; return x, w.getframerate()
def wr(f,x,sr):
    w=wave.open(f,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(x,-1,1)*32767).astype(np.int16).tobytes()); w.close()
src, out, tone_wav, wins = sys.argv[1:5]
subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-vn","-ac","1","-ar","48000","-c:a","pcm_s16le","/tmp/_a.wav"],check=True)
a, sr = rd("/tmp/_a.wav"); a=a.copy(); t, _ = rd(tone_wav)
if t.ndim > 1: t = t.mean(1)
rng = np.random.default_rng(1); f = int(0.015*sr)
def tone(n):
    o = np.zeros(n + len(t)); p = 0; w = np.hanning(len(t))
    while p < n: s = rng.integers(0, max(1, len(t)//4)); seg = np.roll(t, s)*w; o[p:p+len(t)] += seg; p += len(t)//2
    return o[:n]
for w in wins.split(","):
    s, e = (int(float(x)*sr) for x in w.split(":")); n = e - s
    env = np.ones(n); env[:f] = np.linspace(0,1,f); env[-f:] = np.linspace(1,0,f)
    a[s:e] = a[s:e]*(1-env) + tone(n)*env
wr("/tmp/_b.wav", a, sr)
subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-i","/tmp/_b.wav","-map","0:v","-map","1:a","-c:v","copy","-af","highpass=f=80","-c:a","aac","-b:a","192k",out],check=True)
print("wrote", out)
