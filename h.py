from mpmath import mpf, mpc, mpi
from rational import Rational
from integer import Zn
import os

def main(display):
    cmd = "d:/bin/vim/vim71/vim.exe " + \
        "c:/cygwin/home/Don/bin/bat/help_system/index.hld"
    os.system(cmd)
    num = raw_input("Enter number for x register: ")
    if "mpf" in num or \
       "mpc" in num or \
       "mpi" in num or \
       "Rational" in num or \
       "Zn" in num:
        s = "from mpmath import mpf, mpc, mpi\n"
        s += "from rational import Rational\n"
        s += "from integer import Zn\n"
        s += "result = %s\n" % num.strip()
        d = {}
        co = compile(s, "c.py", "exec")
        eval(co, d, d)
        return d["result"]
    else:
        return mpf(num.strip())

