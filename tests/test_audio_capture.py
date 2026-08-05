from voice_capture.desktop.audio_capture import _mix_format_error


def test_mix_format_error_mentions_device_label_and_fix():
    err = _mix_format_error("microfone padrão")

    assert isinstance(err, RuntimeError)
    assert "microfone padrão" in str(err)
    assert "Painel de Controle" in str(err)
    assert "Formato Padrão" in str(err)
