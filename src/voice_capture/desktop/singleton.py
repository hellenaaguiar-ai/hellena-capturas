"""Trava de instancia unica pro listener: evita que duas copias rodem ao
mesmo tempo (ex: usuaria clica no icone "Iniciar Listener" sem saber se
ja tem um rodando) - duas instancias competindo pelos mesmos atalhos
globais causaria comportamento imprevisivel (gravacao duplicada, erro
"hotkey ja registrado", etc.)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional


def _pid_is_running(pid: int) -> bool:
    """So CONSULTA se o processo existe, nunca encerra nada - no Windows,
    os.kill(pid, 0) (o jeito comum no Linux/Mac de so checar) pode na
    pratica ser traduzido para TerminateProcess e matar o processo, entao
    evitamos essa API aqui e usamos OpenProcess do Windows diretamente."""
    import ctypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    return False


def acquire_single_instance_lock(
    lock_path: Path,
    current_pid: int,
    pid_is_running: Callable[[int], bool] = _pid_is_running,
) -> bool:
    """Tenta virar "a" instancia ativa. Retorna True se conseguiu (pode
    seguir rodando normalmente), False se ja existe outra instancia viva
    (quem chamou deve encerrar em seguida, sem erro - e o comportamento
    esperado de clicar duas vezes sem querer)."""
    existing_pid: Optional[int] = None
    if lock_path.exists():
        try:
            existing_pid = int(lock_path.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            existing_pid = None

    if existing_pid is not None and existing_pid != current_pid and pid_is_running(existing_pid):
        return False

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(current_pid), encoding="utf-8")
    return True
