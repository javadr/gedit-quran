#!/usr/bin/env python3

import configparser

from gi.repository import GLib

from dataclasses import dataclass
from pathlib import Path
from quran import Quran

# region ############### CONSTANTs #################################
GEDIT_CONFIG_DIR = Path(GLib.get_user_config_dir())/"gedit"
COFING_FILE = Path(GEDIT_CONFIG_DIR)/"quran_settings.ini"
# endregion ############### CONSTANTs ###############################

@dataclass
class Config:
    config_file = COFING_FILE
    quran = Quran()
    data = configparser.ConfigParser()

    def __init__(self):
        ini_file = self.data.read(self.config_file)
        if not ini_file:
            self.data.read_dict(
                dict(
                    Quran=dict(
                        surah = f"1. {self.quran.suras_ar[0]} ({self.quran.suras_en[0]})",
                        from_ayah = 1,
                        to_ayah = 7,
                    ),
                    Settings=dict(
                        ayah_address = True,
                        newline = False,
                        latex_command = False,
                    ),
                ),
            )

    def __setitem__(self, section, key_values):
        self.data.read_dict({ f"{section}":key_values })
        with open(self.config_file, "w") as configfile:
            self.data.write(configfile)

    def __getitem__(self, section):
        try:
            return self.data[f"{section}"]
        except KeyError:
            return None


if __name__ == "__main__":
    print(COFING_FILE)
    conf = Config()
    # conf['Quran'] = dict(from_ayah=20, to_ayah=100)
    conf["Window Position"] = dict(x=100)
    print(conf["Quran"])