from voice_capture.desktop.singleton import acquire_single_instance_lock


def test_first_instance_acquires_lock(tmp_path):
    lock_path = tmp_path / "listener.pid"

    acquired = acquire_single_instance_lock(lock_path, current_pid=111, pid_is_running=lambda pid: False)

    assert acquired is True
    assert lock_path.read_text(encoding="utf-8") == "111"


def test_second_instance_is_rejected_while_first_still_running(tmp_path):
    lock_path = tmp_path / "listener.pid"
    acquire_single_instance_lock(lock_path, current_pid=111, pid_is_running=lambda pid: True)

    acquired = acquire_single_instance_lock(lock_path, current_pid=222, pid_is_running=lambda pid: pid == 111)

    assert acquired is False
    # o lock continua apontando pra instancia original, nao foi sobrescrito
    assert lock_path.read_text(encoding="utf-8") == "111"


def test_stale_lock_from_dead_process_is_taken_over(tmp_path):
    lock_path = tmp_path / "listener.pid"
    acquire_single_instance_lock(lock_path, current_pid=111, pid_is_running=lambda pid: False)

    # o "111" nao existe mais (pid_is_running sempre False) - a nova instancia
    # deve conseguir assumir o lock normalmente, sem ficar travada pra sempre
    acquired = acquire_single_instance_lock(lock_path, current_pid=222, pid_is_running=lambda pid: False)

    assert acquired is True
    assert lock_path.read_text(encoding="utf-8") == "222"


def test_corrupted_lock_file_is_ignored(tmp_path):
    lock_path = tmp_path / "listener.pid"
    lock_path.write_text("nao-e-um-numero", encoding="utf-8")

    acquired = acquire_single_instance_lock(lock_path, current_pid=333, pid_is_running=lambda pid: True)

    assert acquired is True
    assert lock_path.read_text(encoding="utf-8") == "333"


def test_same_pid_reacquiring_its_own_lock_succeeds(tmp_path):
    lock_path = tmp_path / "listener.pid"
    acquire_single_instance_lock(lock_path, current_pid=111, pid_is_running=lambda pid: True)

    # a mesma instancia (mesmo PID) chamando de novo nao deve ser bloqueada
    # por si mesma
    acquired = acquire_single_instance_lock(lock_path, current_pid=111, pid_is_running=lambda pid: True)

    assert acquired is True
