# -*- coding: utf-8 -*-
import os
import json
from collections import namedtuple
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

from tinydb import TinyDB, Query


MODULE_PATH = os.path.dirname(os.path.dirname(__file__))


Record = namedtuple('Record', [
    'personal_id', 'phone', 'email', 'start_station', 'dest_station',
    'outbound_date', 'outbound_time', 'adult_num', 'child_num',
    'disabled_num', 'elder_num', 'college_num', 'selection_time'
])
Record.__new__.__defaults__ = (0, 0, 0, 0, [])


class RecordFirstPage:
    def __init__(self):
        self.start_station = None
        self.dest_station = None
        self.outbound_date = None
        self.outbound_time = None
        self.preferred_time = None
        self.adult_num = 0
        self.child_num = 0
        self.disabled_num = 0
        self.elder_num = 0
        self.college_num = 0


class RecordTrainPage:
    def __init__(self):
        self.selection_time: list = []


class RecordTicketPage:
    def __init__(self):
        self.personal_id = None
        self.phone = None
        self.email = None


class ReservationDB:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(MODULE_PATH, ".db", "history.json")
        self.db_path = db_path
        db_dir = db_path[: db_path.rfind("/")]
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def save(self, book_model, ticket, train):
        data = Record(
            ticket.personal_id,
            ticket.phone,
            ticket.email,
            book_model.start_station,
            book_model.dest_station,
            book_model.outbound_date,
            book_model.outbound_time,
            book_model.adult_num,
            getattr(book_model, 'child_num', 0),
            getattr(book_model, 'disabled_num', 0),
            getattr(book_model, 'elder_num', 0),
            getattr(book_model, 'college_num', 0),
            train.selection_time,
        )._asdict()
        with TinyDB(self.db_path, sort_keys=True, indent=4) as db:
            hist = db.search(Query().personal_id == ticket.personal_id)
            if self._compare_hist(data, hist) is None:
                db.insert(data)

    def get_history(self):
        with TinyDB(self.db_path) as db:
            dicts = db.all()
        records = []
        for d in dicts:
            d.setdefault('child_num', 0)
            d.setdefault('disabled_num', 0)
            d.setdefault('elder_num', 0)
            d.setdefault('college_num', 0)
            records.append([d.doc_id, Record(**d)])
        return records

    def _compare_hist(self, data, hist):
        for idx, h in enumerate(hist):
            comp = [h[k] for k in data.keys() if h[k] == data[k]]
            if len(comp) == len(data):
                return idx
        return None

    def remove(self, idx):
        with TinyDB(self.db_path) as db:
            db.remove(doc_ids=[idx])


@dataclass
class UserProfile:
    profile_name: str
    personal_ids: List[str]
    phone: str
    email: str
    created_at: str = None
    last_used: str = None


class UserProfileManager:
    def __init__(self, profiles_file: str = None):
        if profiles_file is None:
            profiles_dir = os.path.join(MODULE_PATH, ".db")
            if not os.path.exists(profiles_dir):
                os.makedirs(profiles_dir)
            profiles_file = os.path.join(profiles_dir, "user_profiles.json")
        self.profiles_file = profiles_file
        self.profiles: Dict[str, UserProfile] = self._load_profiles()

    def _load_profiles(self) -> Dict[str, UserProfile]:
        if not os.path.exists(self.profiles_file):
            return {}
        try:
            with open(self.profiles_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                profiles = {}
                for name, profile_data in data.items():
                    profiles[name] = UserProfile(**profile_data)
                return profiles
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_profiles(self):
        data = {}
        for name, profile in self.profiles.items():
            data[name] = asdict(profile)
        with open(self.profiles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_profile(self, profile: UserProfile) -> bool:
        if not profile.created_at:
            profile.created_at = datetime.now().isoformat()
        profile.last_used = datetime.now().isoformat()
        self.profiles[profile.profile_name] = profile
        self._save_profiles()
        return True

    def get_profile(self, profile_name: str) -> Optional[UserProfile]:
        return self.profiles.get(profile_name)

    def list_profiles(self) -> List[str]:
        return list(self.profiles.keys())

    def delete_profile(self, profile_name: str) -> bool:
        if profile_name in self.profiles:
            del self.profiles[profile_name]
            self._save_profiles()
            return True
        return False

    def update_last_used(self, profile_name: str):
        if profile_name in self.profiles:
            self.profiles[profile_name].last_used = datetime.now().isoformat()
            self._save_profiles()

    def profile_exists(self, profile_name: str) -> bool:
        return profile_name in self.profiles


class TrainCache:
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(current_dir, "..", ".db")
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_file = os.path.join(cache_dir, "timetable_cache.json")
        self.cache_data = self._load_cache()

    def _load_cache(self) -> Dict:
        if not os.path.exists(self.cache_file):
            return {"version": "2.0", "created_at": datetime.now().isoformat(), "caches": {}}
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "caches" not in data:
                    data["caches"] = {}
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {"version": "2.0", "created_at": datetime.now().isoformat(), "caches": {}}

    def _save_cache(self):
        try:
            self.cache_data["last_updated"] = datetime.now().isoformat()
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存緩存失敗: {e}")

    def is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.cache_data["caches"]:
            return False
        try:
            cached_date = self.cache_data["caches"][cache_key].get("tdx_date", "")
            today = datetime.now().strftime("%Y-%m-%d")
            return cached_date == today
        except (KeyError, TypeError):
            return False

    def get_cached_trains(self, cache_key: str) -> Optional[List[Dict]]:
        if not self.is_cache_valid(cache_key):
            return None
        try:
            return self.cache_data["caches"][cache_key]["trains_data"]
        except KeyError:
            return None

    def cache_trains(self, cache_key: str, trains_data: List[Dict], tdx_date: str = None):
        if not trains_data:
            return
        try:
            self.cache_data["caches"][cache_key] = {
                "tdx_date": tdx_date,
                "cached_time": datetime.now().timestamp(),
                "total_trains": len(trains_data),
                "trains_data": trains_data,
            }
            self._save_cache()
        except Exception as e:
            print(f"緩存列車數據失敗: {e}")

    def get_cache_stats(self) -> Dict:
        valid_caches = 0
        total_trains = 0
        for cache_key, cache_info in self.cache_data["caches"].items():
            if self.is_cache_valid(cache_key):
                valid_caches += 1
                total_trains += cache_info.get("total_trains", 0)
        return {
            "total_caches": len(self.cache_data["caches"]),
            "valid_caches": valid_caches,
            "total_trains": total_trains,
            "cache_file_size": self._get_file_size(),
            "last_updated": self.cache_data.get("last_updated", "未知")
        }

    def _get_file_size(self) -> str:
        try:
            if os.path.exists(self.cache_file):
                size_bytes = os.path.getsize(self.cache_file)
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"
            return "0 B"
        except Exception:
            return "未知"

    def clear_invalid_cache(self):
        invalid_keys = [k for k in self.cache_data["caches"] if not self.is_cache_valid(k)]
        for key in invalid_keys:
            del self.cache_data["caches"][key]
        if invalid_keys:
            self._save_cache()
            print(f"清理了 {len(invalid_keys)} 個無效緩存")

    def clear_all_cache(self):
        self.cache_data = {"version": "2.0", "created_at": datetime.now().isoformat(), "caches": {}}
        self._save_cache()
        print("已清空所有緩存")

    def remove_cache(self, cache_key: str):
        if cache_key in self.cache_data["caches"]:
            del self.cache_data["caches"][key]
        self._save_cache()
