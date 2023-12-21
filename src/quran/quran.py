import gzip

from pathlib import Path
from typing import Tuple, List, Union, Optional

# region ############### CONSTANTs #################################
SOURCE_DIR = Path(__file__).parent.resolve()
# endregion ############### CONSTANTs ###############################


class Quran:
    suras_en: Tuple[str]
    suras_ar: Tuple[str]
    suras_ayat: Tuple[int]
    quran_text: Tuple[str]
    line_index: Tuple[int]
    quran_file: Union[Path, str] = SOURCE_DIR/"quran.txt.gz"
    quran_data: Union[Path, str] = SOURCE_DIR/"quran.data"

    def __init__(self):
        with open(self.quran_data) as quran_data_file:
            sa, se, st = quran_data_file.readlines()[:3]
        self.suras_ar = sa.strip().split(",")
        self.suras_en = se.strip().split(",")
        self.suras_ayat = tuple(map(int, st.strip().split(",")))
        self.line_index = self._create_index()

    def _create_index(self) -> Tuple[int]:
        index = []
        position = 0
        with gzip.open(self.quran_file, "rt") as gzipped_file:
            for _ in range(6236):
                gzipped_file.readline()
                index.append(position)
                position = gzipped_file.tell()
        return tuple(index)

    def get_verse(
            self, sura: int,
            from_ayah: int, to_ayah: Optional[int] = None,
            ) -> List[Tuple[str, int]]:
        Ayat: List[Tuple[str, int]] = []
        if to_ayah is None:
            to_ayah = from_ayah
        with gzip.open(self.quran_file, "rt") as gzipped_file:
            line_number = sum(self.suras_ayat[:sura-1]) + from_ayah # first ayah
            for ayah in range(to_ayah - from_ayah + 1):
                gzipped_file.seek(self.line_index[line_number - 1 + ayah])
                num, verse = gzipped_file.readline().strip().split("|")[1:]
                Ayat.append((verse, num))
        return Ayat