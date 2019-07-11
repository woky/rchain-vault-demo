import random

def randseed(rnd: random.Random):
    return rnd.randrange(0, 1 << 32)
