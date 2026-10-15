"""Model profiles and plaintext keys in portable data; keyring is read-only legacy import."""
import copy
import json
from pathlib import Path
import uuid
import settings
from storage_paths import atomic_json


def new_profile(name="新模型配置", service="openai"):
    identifier = uuid.uuid4().hex
    return {"id": identifier, "name": name, "service": service, "base_url": "",
            "model": "", "credential": "llm_profile_" + identifier}


def load_profiles():
    config = settings.load_settings()
    if "model_profiles" not in config:
        profile = new_profile("原有 PopTrans" if config.get("llm_service") == "poptrans" else "原有模型配置")
        profile.update(service=config.get("llm_service", "openai"),
                       base_url=config.get("llm_base_url", ""), model=config.get("llm_model", ""),
                       credential="llm_key" if config.get("llm_service", "openai") == "openai" and
                       any(k in config for k in ("llm_base_url", "llm_model", "llm_service")) else profile["credential"])
        state = {"profiles": [profile], "active_id": profile["id"]}
        save_profiles(state)
        _migrate_keys(state)
        return state
    state = {"profiles": copy.deepcopy(config["model_profiles"]),
             "active_id": config.get("active_model_profile")}
    _validate(state)
    _migrate_keys(state)
    return state


def _validate(state):
    profiles = state["profiles"]
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("模型配置列表为空或已损坏")
    ids = [p["id"] for p in profiles]
    if len(set(ids)) != len(ids) or state["active_id"] not in ids:
        raise ValueError("模型配置标识或启用状态已损坏")
    for p in profiles:
        if p["service"] not in ("openai", "poptrans"):
            raise ValueError("未知模型接口类型")
        if not all(isinstance(p[k], str) for k in ("id", "name", "service", "base_url", "model", "credential")):
            raise ValueError("模型参数格式错误")


def save_profiles(state):
    _validate(state)
    config = settings.load_settings()
    # Store a strict whitelist: keys must never accidentally reach settings.json.
    config["model_profiles"] = [{k: p[k] for k in ("id", "name", "service", "base_url", "model", "credential")}
                                for p in state["profiles"]]
    config["active_model_profile"] = state["active_id"]
    settings.save_settings(config)


def active_profile():
    state = load_profiles()
    return next(p for p in state["profiles"] if p["id"] == state["active_id"])


def profile_key(profile):
    if profile["service"] == "poptrans":
        return ""
    values = _load_keys()
    identifier = profile["credential"]
    if identifier in values:
        return values[identifier]
    try:
        import keyring
        value = keyring.get_password(settings.APP_NAME, identifier) or ""
    except Exception:
        return ""
    # Copy existing credentials without deleting or updating the legacy store.
    values[identifier] = value
    _save_keys(values)
    return value


def save_profile_key(profile, key):
    if profile["service"] == "poptrans":
        return
    values = _load_keys()
    # Keep an explicit empty value so clearing cannot resurrect a legacy key.
    values[profile["credential"]] = key
    _save_keys(values)


def _keys_file():
    return Path(settings._config_dir()) / "api_keys.json"


def _load_keys():
    try:
        with _keys_file().open(encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("keys"), dict):
        raise ValueError("api_keys.json 格式错误，请检查便携密钥文件")
    values = data["keys"]
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
        raise ValueError("api_keys.json 密钥格式错误")
    return values


def _save_keys(values):
    atomic_json(_keys_file(), {"schema": 1, "keys": values})


def _migrate_keys(state):
    # Import inactive profiles too, so all configured keys live in data.
    for profile in state["profiles"]:
        profile_key(profile)
