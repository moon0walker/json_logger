#!/usr/bin/python3

import os
import json
import multiprocessing
from JSONLogger import LoggerManager


def StartProc(Args):
    log, index = Args
    log.print.info("logs/{0}.log".format( os.getpid() ), "i'm a {0}".format(os.getpid()))
    log.print.error("logs/{0}.log".format( os.getpid() ), "i'm a {0}".format(os.getpid() ))
    log.print.warning("logs/{0}.log".format( os.getpid() ), "i'm a {0}".format(os.getpid()))
    log.print.success("logs/{0}.log".format( os.getpid() ), "i'm a {0}".format(os.getpid()))


def pool(iterlength=10, procnum=3):
    log = LoggerManager()
    pool = multiprocessing.Pool(procnum)
    pool.map(StartProc, [(log, ind) for ind in list(range(0, iterlength))])
    pool.close()
    pool.join()
    pool.terminate()


def test_json_integrity():
    for fl in os.listdir("logs"):
        try:
            json.load(open(os.path.join("logs", fl)))
            # print('SUCCESS {0}'.format(fl))
        except:
            print('ERROR {0}'.format(fl))


if __name__ == '__main__':
    pool(iterlength=20, procnum=10)
    test_json_integrity()
