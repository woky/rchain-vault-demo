import math
from typing import Optional

LETTER_NAMES = '''
    Alfa Bravo Charlie Delta Echo Foxtrot Golf Hotel India Juliett Kilo Lima
    Mike November Oscar Papa Quebec Romeo Sierra Tango Uniform Victor Whiskey
    Xray Yankee Zulu
'''.strip().split()

DIGIT_NAMES = 'Zero One Two Three Four Five Six Seven Eight Nine'.split()


class PhoneticNames:

    def __init__(self, max_index: Optional[int] = None, sep: str = ' '):
        self.digits = math.ceil(math.log10(max_index / 26)) if max_index else 0
        self.sep = sep

    def __getitem__(self, num: int) -> str:
        parts = [LETTER_NAMES[num % 26]]
        num //= 26
        digits = 0
        while num > 0 or digits < self.digits:
            parts.append(DIGIT_NAMES[num % 10])
            num //= 10
            digits += 1
        return self.sep.join(parts)
