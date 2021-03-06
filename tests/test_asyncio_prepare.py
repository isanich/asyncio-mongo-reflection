import asyncio
import motor.motor_asyncio
import pytest
from functools import wraps

from asyncio_mongo_reflection.deque_reflection import *
from asyncio_mongo_reflection.dict_reflection import *

loop = asyncio.get_event_loop_policy().new_event_loop()
asyncio.set_event_loop(loop)
loop.set_debug(False)
loop._close = loop.close
loop.close = lambda: None

lrun_uc = loop.run_until_complete

client = motor.motor_asyncio.AsyncIOMotorClient()
db = client.test_db


@pytest.fixture(scope="session", autouse=True)
def test_shutdown():
    yield None
    # clear all tasks before loop stops
    pending = asyncio.Task.all_tasks()
    for task in pending:
        task.cancel()

    lrun_uc(asyncio.sleep(1))
    loop.close()


def async_test(testf):
    @wraps(testf)
    def tmp(*args, **kwargs):
        return lrun_uc(testf(*args, **kwargs))
    return tmp


def flattern_list_nested(nlist, dumps=None, lists_to_deque=True):
    fdumps = lambda arg: dumps(arg) if callable(dumps) else arg

    for ix, el in enumerate(nlist):
        if isinstance(el, DequeReflection) or isinstance(el, deque):
            if lists_to_deque:
                nlist[ix] = deque(list(el), maxlen=el.maxlen)
            else:
                nlist[ix] = list(el)
            flattern_list_nested(nlist[ix], dumps=dumps, lists_to_deque=lists_to_deque)
        elif isinstance(el, DictReflection) or type(el) is dict:
            nlist[ix] = flattern_dict_nested(dict(el), dumps, lists_to_deque=lists_to_deque)
        else:
            nlist[ix] = fdumps(el)

    return nlist


def flattern_dict_nested(dct, dumps=None, lists_to_deque=False):
    fdumps = lambda arg: dumps(arg) if callable(dumps) else arg

    for key, val in dct.items():
        if isinstance(val, DictReflection) or isinstance(val, dict):
            dct[key] = flattern_dict_nested(dict(val), dumps, lists_to_deque=lists_to_deque)
        elif type(val) is list or isinstance(val, DequeReflection) or isinstance(val, deque):
            val = deque(val) if lists_to_deque else list(val)
            dct[key] = flattern_list_nested(val, dumps, lists_to_deque=lists_to_deque)
        else:
            dct[key] = fdumps(val)
    return dct


def compare_nested_dict(m, tested):
    for key, val in tested.items():
        if isinstance(val, DictReflection):
            assert hasattr(val, '_deque_cls')
            compare_nested_dict(m[key], val)
        elif isinstance(val, DequeReflection):
            assert hasattr(val, '_dict_cls')
            compare_nested_list(m[key], val)

        assert m[key] == val
        assert m.key == tested.key


def compare_nested_list(m, tested):
    for ix, el in enumerate(tested):
        if isinstance(el, DequeReflection):
            assert hasattr(el, '_dict_cls')
            compare_nested_list(m[ix], el)
        elif isinstance(el, DictReflection):
            assert hasattr(el, '_deque_cls')
            compare_nested_dict(m[ix], el)

        assert m[ix] == el
        # assert m.maxlen == tested.maxlen
        assert m.key == tested.key


async def mongo_compare(ex, m):
    obj = await db[m.col.name].find_one(m.obj_ref)

    nested = m.key.split(sep='.')
    for k in nested:
        obj = obj[k]

    assert obj == ex
