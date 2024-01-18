import bz2
import pickle

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, List, Union, Optional

# region ############### CONSTANTs #################################
SOURCE_DIR = Path(__file__).parent.resolve()
# endregion ############### CONSTANTs ###############################


@dataclass
class Quran:
    suras_en: Tuple[str]
    suras_ar: Tuple[str]
    suras_ayat: Tuple[int]
    quran_text: Tuple[str]
    line_index: Tuple[int]
    quran_file: Union[Path, str] = SOURCE_DIR/"quran.txt.bz2"
    quran_data: Union[Path, str] = SOURCE_DIR/"quran.metadata"
    quran_indices: Union[Path, str] = SOURCE_DIR/"quran-idx.pkl.bz2"

    def __init__(self):
        with open(self.quran_data) as quran_data_file:
            sa, se, st = quran_data_file.readlines()[:3]
        self.suras_ar = sa.strip().split(",")
        self.suras_en = se.strip().split(",")
        self.suras_ayat = tuple(map(int, st.strip().split(",")))
        self.line_index = self._get_indices()

    def _get_indices(self):
        if Path(self.quran_indices).exists():
            with bz2.open(self.quran_indices, "rb") as bz2_file:
                return pickle.load(bz2_file)
        else:
            indices = self._create_index()
            with bz2.open(self.quran_indices, "wb") as bz2_file:
                pickle.dump(indices, bz2_file)
            return indices

    def _create_index(self) -> Tuple[int]:
        index = []
        position = 0
        with bz2.open(self.quran_file, "rt") as bz2_file:
            for _ in range(6236):
                bz2_file.readline()
                index.append(position)
                position = bz2_file.tell()
        return tuple(index)

    def get_verse(
            self, surah: int,
            from_ayah: int, to_ayah: Optional[int] = None,
            ) -> List[Tuple[str, int]]:
        Ayat: List[Tuple[str, int]] = []
        if to_ayah is None:
            to_ayah = from_ayah
        with bz2.open(self.quran_file, "rt") as bz2_file:
            line_number = sum(self.suras_ayat[:surah-1]) + from_ayah # first ayah
            for ayah in range(to_ayah - from_ayah + 1):
                bz2_file.seek(self.line_index[line_number - 1 + ayah])
                num, verse = bz2_file.readline().strip().split("|")[1:]
                Ayat.append((verse, num))
        return Ayat

    def latex(
            self,
            surah: int,
            from_ayah: int,
            to_ayah: int,
            ) -> str:
            if from_ayah==1 and to_ayah==self.suras_ayat[surah-1]:
                latex_cmd = f"\\quransurah[{self.suras_en[surah-1]}]"
            else:
                latex_cmd = f"\\quranayah[{self.suras_en[surah-1]}]"
                latex_cmd += f"[{from_ayah}"
                latex_cmd += f"-{to_ayah}]" if from_ayah!=to_ayah else "]"
            return latex_cmd