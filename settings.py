"""配置与阅读位置记录。

数据统一保存到程序目录下的 data，保留旧接口供阅读窗口调用。
"""

import json
import os
from pathlib import Path
from storage_paths import data_dir, atomic_json, application_dir

APP_NAME = "PDFTranslator"


def _config_dir() -> str:
    """返回程序旁的便携数据目录。"""
    return str(data_dir())


def _positions_file() -> str:
    return os.path.join(_config_dir(), "reading_positions.json")


def _settings_file() -> str:
    return os.path.join(_config_dir(), "settings.json")


def chatnotes_dir() -> str:
    """便携问答笔记目录。"""
    path = os.path.join(_config_dir(), "chatnotes")
    os.makedirs(path, exist_ok=True)
    return path


def _recent_file() -> str:
    return os.path.join(_config_dir(), "recent.json")


MAX_RECENT = 10


def _stored_pdf_path(pdf_path: str) -> str:
    try:
        relative = Path(pdf_path).resolve().relative_to(application_dir())
        return "@portable/" + relative.as_posix()
    except ValueError:
        return str(Path(pdf_path).resolve())


def _resolved_pdf_path(pdf_path: str) -> str:
    if pdf_path.startswith("@portable/"):
        return str(application_dir() / pdf_path[len("@portable/"):])
    return pdf_path


def load_recent() -> list:
    """加载最近打开的文件列表（最新的在前）。"""
    try:
        with open(_recent_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [_resolved_pdf_path(p) for p in data if isinstance(p, str)]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def add_recent(pdf_path: str) -> None:
    """把文件加入最近打开列表（去重，最新的在前）。"""
    recent = load_recent()
    if pdf_path in recent:
        recent.remove(pdf_path)
    recent.insert(0, pdf_path)
    recent = recent[:MAX_RECENT]
    try:
        atomic_json(Path(_recent_file()), [_stored_pdf_path(p) for p in recent])
    except OSError:
        pass


def remove_recent(pdf_path: str) -> None:
    """从最近打开列表移除指定文件。"""
    recent = load_recent()
    if pdf_path in recent:
        recent.remove(pdf_path)
        try:
            atomic_json(Path(_recent_file()), [_stored_pdf_path(p) for p in recent])
        except OSError:
            pass


def clear_recent() -> None:
    """清空最近打开列表。"""
    try:
        atomic_json(Path(_recent_file()), [])
    except OSError:
        pass


def load_positions() -> dict:
    """加载所有 PDF 的阅读位置记录。"""
    try:
        with open(_positions_file(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_position(pdf_path: str, page: int, scroll: int = 0) -> None:
    """保存某个 PDF 的阅读位置。"""
    positions = load_positions()
    positions[_stored_pdf_path(pdf_path)] = {"page": page, "scroll": scroll}
    try:
        atomic_json(Path(_positions_file()), positions)
    except OSError:
        pass


def get_position(pdf_path: str) -> dict | None:
    """获取某个 PDF 的阅读位置，无则返回 None。"""
    positions = load_positions()
    return positions.get(_stored_pdf_path(pdf_path)) or positions.get(pdf_path)


def load_settings() -> dict:
    """加载界面设置（如分栏宽度）。"""
    try:
        with open(_settings_file(), "r", encoding="utf-8") as f:
            value = json.load(f)
            if not isinstance(value, dict):
                raise ValueError("settings.json 必须是 JSON 对象")
            return value
    except FileNotFoundError:
        return {}


def save_settings(settings: dict) -> None:
    """保存界面设置。"""
    atomic_json(Path(_settings_file()), settings)


def get_llm_key() -> str:
    from model_profiles import active_profile, profile_key
    return profile_key(active_profile())


def save_llm_key(api_key: str) -> None:
    from model_profiles import active_profile, save_profile_key
    save_profile_key(active_profile(), api_key)


def get_llm_base_url() -> str:
    """获取大模型接口地址。"""
    from model_profiles import active_profile
    return active_profile()["base_url"]


def get_llm_model() -> str:
    """获取大模型名称。"""
    from model_profiles import active_profile
    return active_profile()["model"]


def save_llm_config(base_url: str, model: str, service: str = "openai") -> None:
    """保存大模型接口地址和模型名。"""
    from model_profiles import load_profiles, save_profiles
    state = load_profiles()
    for profile in state["profiles"]:
        if profile["id"] == state["active_id"]:
            profile.update(base_url=base_url, model=model, service=service)
    save_profiles(state)


def get_llm_service() -> str:
    from model_profiles import active_profile
    return active_profile()["service"]
