#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper


def disable(func):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''

    return func


def decorator(deco):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    def wrapper(func):
        update_wrapper(deco, func)
        return deco
    return wrapper


def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''
    def countwrapper(*args):
        countwrapper.calls += 1
        return func(*args)

    countwrapper.calls = 0
    update_wrapper(countwrapper, func)
    return countwrapper


def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    results = {}
    def memowrapper(*args):
        if not args in results:
            results[args] = func(*args)
            if hasattr(func, 'calls'):
                setattr(memowrapper, 'calls', func.calls)
        return results[args]
    update_wrapper(memowrapper, func)
    return memowrapper


def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''

    def wrapper(*args):
        length = len(args)
        if length > 2:
            return func(args[0], wrapper(*args[1:]))
        elif length == 2:
            return func(args[0], args[1])
        elif length == 1:
            return args[0]
    update_wrapper(wrapper, func)
    return wrapper


def trace(s):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''
    def deco(func):
        def tracewrapper(*args):
            tracewrapper.i += 1
            a = ', '.join(map(repr, args))
            print ''.join([s * tracewrapper.i,
                           ' --> ', func.__name__, '(', a, ')']
                          )
            res = func(*args)
            print ''.join([s * tracewrapper.i,
                           ' <-- ', func.__name__, '(', a, ')', ' == ', str(res)]
                          )
            tracewrapper.i -= 1
            return res
        update_wrapper(tracewrapper, func)
        tracewrapper.i = -1
        return tracewrapper
    return deco

@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)

def main():
    print foo(4, 3)
    print foo(4, 3, 2)
    print foo(4, 3)
    print "foo was called", foo.calls, "times"

    print bar(4, 3)
    print bar(4, 3, 2)
    print bar(4, 3, 2, 1)
    print "bar was called", bar.calls, "times"

    print fib.__doc__
    fib(3)
    print fib.calls, 'calls made'


if __name__ == '__main__':
    main()
