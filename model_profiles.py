"""Model profile persistence and independent system credentials; no UI dependency."""
import copy
import uuid
import settings


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
        return state
    state = {"profiles": copy.deepcopy(config["model_profiles"]),
             "active_id": config.get("active_model_profile")}
    _validate(state)
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
    try:
        import keyring
        return keyring.get_password(settings.APP_NAME, profile["credential"]) or ""
    except Exception:
        return ""


def save_profile_key(profile, key):
    if profile["service"] == "poptrans":
        return
    import keyring
    if key:
        keyring.set_password(settings.APP_NAME, profile["credential"], key)
    elif keyring.get_password(settings.APP_NAME, profile["credential"]):
        keyring.delete_password(settings.APP_NAME, profile["credential"])
