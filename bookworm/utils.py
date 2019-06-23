import random

def random_hash():
    return ("%032x" % random.getrandbits(128))[:10]

def ip_from_decimal(dec):
    return ".".join([str(int(b, 2)) for b in b_octets(bin(dec)[2:])])

def b_octets(l):
    l = l.zfill(32)
    return [l[0:8], l[8:16], l[16:24], l[24:32]]
