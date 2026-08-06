"""Script isolado pra testar se a captura de loopback (audio do sistema)
funciona nesse computador, sem passar pelo listener/threads do projeto -
ajuda a isolar se o problema e no pyaudiowpatch/driver ou na nossa
integracao com ele.

Uso:
  .venv\\Scripts\\python.exe scripts\\windows\\diagnostico_loopback.py
"""
import wave

import pyaudiowpatch as pyaudio

print("1. Abrindo PyAudio...")
p = pyaudio.PyAudio()
print("   OK")

print("2. Pegando info do WASAPI...")
wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
print("   OK:", wasapi_info["name"])

print("3. Pegando dispositivo de saida padrao...")
default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
print("   OK:", default_speakers["name"])

if not default_speakers["isLoopbackDevice"]:
    print("4. Procurando equivalente de loopback...")
    found = None
    for loopback in p.get_loopback_device_info_generator():
        print("   candidato:", loopback["name"])
        if default_speakers["name"] in loopback["name"]:
            found = loopback
            break
    if found is None:
        print("   NAO ENCONTROU loopback correspondente.")
        p.terminate()
        raise SystemExit(1)
    default_speakers = found

print("5. Dispositivo de loopback escolhido:", default_speakers["name"], "index=", default_speakers["index"])

print("6. Abrindo stream de gravacao por 3 segundos (toque algum som agora)...")
stream = p.open(
    format=pyaudio.paInt16,
    channels=int(default_speakers["maxInputChannels"]) or 2,
    rate=int(default_speakers["defaultSampleRate"]) or 48000,
    input=True,
    input_device_index=default_speakers["index"],
    frames_per_buffer=4800,
)

frames = []
import time

start = time.time()
while time.time() - start < 3:
    frames.append(stream.read(4800, exception_on_overflow=False))

stream.stop_stream()
stream.close()
p.terminate()

print("7. Gravou", len(frames), "blocos. Salvando teste_loopback.wav...")
with wave.open("teste_loopback.wav", "wb") as wf:
    wf.setnchannels(int(default_speakers["maxInputChannels"]) or 2)
    wf.setsampwidth(2)
    wf.setframerate(int(default_speakers["defaultSampleRate"]) or 48000)
    wf.writeframes(b"".join(frames))

print("PRONTO. Se chegou ate aqui sem fechar sozinho, o problema e na integracao, nao na biblioteca.")
