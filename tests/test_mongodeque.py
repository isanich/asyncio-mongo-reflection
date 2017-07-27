from copy import deepcopy
from json import dumps, loads

import motor.motor_asyncio
import pytest
from asyncio_mongo_reflection.mongodeque import *

test_data = []

loop = asyncio.new_event_loop()
loop.set_debug(True)
asyncio.set_event_loop(loop)

run = lambda coro: loop.run_until_complete(coro)

client = motor.motor_asyncio.AsyncIOMotorClient()
db = client.test_db

run(db['test_arr_int'].remove())
run(db['test_arr_str'].remove())
run(db['test_arr_obj'].remove())

MAX_LEN = 7

mongo_int = run(MongoDequeReflection.create([0, 4, 3, 33, 5, deque([1, 2, 3], maxlen=5), 2, 53, 4, 5],
                                            col=db['test_arr_int'],
                                            obj_ref={'array_id': 'test_deque'},
                                            key='inner.arr',
                                            dumps=None, maxlen=MAX_LEN))

mongo_str = run(MongoDequeReflection.create([1, 2, 3, 4, 5],
                                            col=db['test_arr_str'],
                                            obj_ref={'array_id': 'test_deque'},
                                            key='inner.arr',
                                            dumps=str, maxlen=MAX_LEN+1))

mongo_obj = run(MongoDequeReflection.create([{'a': 1}, {'b': 1}, {'c': 1}, {'d': 1}, {'e': 1}],
                                            col=db['test_arr_obj'],
                                            obj_ref={'array_id': 'test_deque'},
                                            key='inner.arr',
                                            dumps=dumps,
                                            loads=loads, maxlen=MAX_LEN+2))


async def mongo_compare(ex, col, obj_ref, akey):
    obj = await col.find_one(obj_ref)

    nested = akey.split(sep='.')
    for key in nested:
        obj = obj[key]

    assert obj == ex


def db_compare(m, o):
    run(mongo_compare(flattern_nested(list(o), dumps=m._dumps, to_deque=False), m.col, m.obj_ref, m.key))


def flattern_nested(nlist, dumps=False, to_deque=True):
    fdumps = lambda arg: dumps(arg) if callable(dumps) else arg

    for ix, el in enumerate(nlist):
        if isinstance(el, MongoDequeReflection) or isinstance(el, deque):
            if to_deque:
                nlist[ix] = deque(list(el), maxlen=el.maxlen)
            else:
                nlist[ix] = list(el)
                flattern_nested(nlist[ix], dumps=dumps, to_deque=to_deque)
        else:
            nlist[ix] = fdumps(el)

    return nlist


@pytest.yield_fixture(scope='session', autouse=True)
def db_conn():
    global mongo_int
    global mongo_str
    global mongo_obj

    yield 1
    # clear remaining tasks
    del mongo_int
    del mongo_str
    del mongo_obj
    pending = asyncio.Task.all_tasks()
    for task in pending:
        task.cancel()
    run(asyncio.sleep(2))
    loop.close()


@pytest.fixture(scope="function",
                params=[mongo_int, mongo_str, mongo_obj],
                ids=['int', 'str', 'obj'])
def _(request):
    return request.param, flattern_nested(deque(list(request.param), maxlen=request.param.maxlen))


def test_create(_):
    m, o = _[0], _[1]
    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_append(_):
    m, o = _[0], _[1]

    m.append(m[-1])
    o.append(o[-1])

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_appendleft(_):
    m, o = _[0], _[1]

    m.appendleft(m[-1])
    o.appendleft(o[-1])

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_extend(_):
    m, o = _[0], _[1]

    m.extend([m[0], m[-2]])
    o.extend([o[0], o[-2]])

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_extendleft(_):
    m, o = _[0], _[1]

    m.extendleft([m[0], m[-2]])
    o.extendleft([o[0], o[-2]])

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_insert(_):
    m, o = _[0], _[1]

    try:
        m.insert(3, 55)
        o.insert(3, 55)
    except IndexError:
        pass

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_pop(_):
    m, o = _[0], _[1]

    m.pop()
    o.pop()

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_popleft(_):
    m, o = _[0], _[1]

    m.popleft()
    o.popleft()

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_nested(_):
    m, o = _[0], _[1]

    m[1] = [1, 2, 53]
    m[1].appendleft(m[2])
    m[1].append(m[3])
    m[2] = deque([23, 41, 2])
    m[2].append(m[1])
    m[2][-1].append(777)

    o[1] = deque([1, 2, 53])
    o[1].appendleft(o[2])
    o[1].append(o[3])
    o[2] = deque([23, 41, 2])
    o[2].append(deepcopy(o[1]))
    o[2][-1].append(777)

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_remove(_):
    m, o = _[0], _[1]

    m.remove(m[1])
    o.remove(o[1])

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_reverse(_):
    m, o = _[0], _[1]

    m.reverse()
    o.reverse()

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_rotate(_):
    m, o = _[0], _[1]

    m.rotate(2)
    o.rotate(2)

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_rotate_neg(_):
    m, o = _[0], _[1]

    m.rotate(-2)
    o.rotate(-2)

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_setitem(_):
    m, o = _[0], _[1]

    m[0] = m[-1]
    o[0] = o[-1]

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_delitem(_):
    m, o = _[0], _[1]

    del m[0]
    del o[0]

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_add(_):
    m, o = _[0], _[1]

    m = m + m
    o = o + o

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_iadd(_):
    m, o = _[0], _[1]

    m += m
    o += o

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_imul(_):
    m, o = _[0], _[1]

    m *= 3
    o *= 3

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_mul(_):
    m, o = _[0], _[1]

    m = m * 3
    o = o * 3

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)


def test_rmul(_):
    m, o = _[0], _[1]

    m = 3 * m
    o = 3 * o

    run(m.mongo_pending.join())
    assert m == o
    db_compare(m, o)