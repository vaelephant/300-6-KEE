from pathlib import Path

from app.services import model_settings as ms


def test_model_settings_overlay_mask_and_update(tmp_path, monkeypatch):
    overlay = tmp_path / "data" / "model_settings.json"
    overlay.parent.mkdir(parents=True)
    monkeypatch.setattr(ms, "_OVERLAY_PATH", overlay)
    monkeypatch.setattr(ms, "_overlay", {})

    view = ms.public_view()
    assert "llm" in view
    assert "api_key_set" in view["llm"]

    updated = ms.update_settings(
        {
            "llm": {
                "base_url": "http://127.0.0.1:11434/v1",
                "api_key": "sk-secret-key",
                "model": "qwen2.5",
            },
            "embedding": {"provider": "local", "model": "hash"},
        }
    )
    assert updated["llm"]["model"] == "qwen2.5"
    assert updated["llm"]["api_key_set"] is True
    assert "sk-secret" not in updated["llm"]["api_key"]
    assert "****" in updated["llm"]["api_key"]

    # empty api_key keeps previous
    again = ms.update_settings({"llm": {"model": "llama3", "api_key": ""}})
    assert again["llm"]["model"] == "llama3"
    assert again["llm"]["api_key_set"] is True

    eff = ms.effective()
    assert eff.llm.api_key == "sk-secret-key"
    assert eff.llm.model == "llama3"
    assert overlay.exists()
