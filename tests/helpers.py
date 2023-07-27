import random
import sys

RANDOM = random.Random(b"bA\xcd\x00\xa9$\xa7\x17\x1c\x10")


# TODO: Remove when dropping 3.9
if sys.version_info < (3, 9):

    def randbytes(n: int) -> bytes:
        return bytearray(RANDOM.getrandbits(8) for _ in range(n))

else:
    randbytes = RANDOM.randbytes
