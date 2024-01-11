#!/usr/bin/env python3

import json

from gi.repository import GLib

from dataclasses import dataclass
from pathlib import Path
from quran import Quran

# region ############### CONSTANTs #################################
GEDIT_CONFIG_DIR = Path(GLib.get_user_config_dir())/"gedit"
COFING_FILE = Path(GEDIT_CONFIG_DIR)/"quran_settings.json"
# endregion ############### CONSTANTs ###############################

@dataclass
class Config:
    config_file = COFING_FILE
    quran = Quran()
    data = dict()

    def __init__(self):
        try:
            with open(COFING_FILE, encoding="utf-8") as conf:
                data = conf.read()
                self.data = json.loads(data)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = dict(
                surah=f"1. {quran.suras_ar[0]} ({quran.suras_en[0]})",
                from_ayah=1,
                to_ayah=7,
            )

    def __setitem__(self, key, value):
        with open(self.config_file, mode="w", encoding="utf-8") as conf:
            self.data[key]=value
            json.dump(self.data, conf)

    def __getitem__(self, key=None):
        return self.data[key]


if __name__ == "__main__":
    print(COFING_FILE)
    Config('to_ayah', 100)
    print(Config['to_ayah'])