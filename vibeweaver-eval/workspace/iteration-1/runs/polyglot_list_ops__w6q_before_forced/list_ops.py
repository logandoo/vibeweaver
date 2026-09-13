def append(list1, list2):
    result = []
    for item in list1:
        result = result + [item]
    for item in list2:
        result = result + [item]
    return result


def concat(lists):
    result = []
    for lst in lists:
        for item in lst:
            result = result + [item]
    return result


def filter(function, list):
    result = []
    for item in list:
        if function(item):
            result = result + [item]
    return result


def length(list):
    count = 0
    for item in list:
        count = count + 1
    return count


def map(function, list):
    result = []
    for item in list:
        result = result + [function(item)]
    return result


def foldl(function, list, initial):
    accumulator = initial
    for item in list:
        accumulator = function(accumulator, item)
    return accumulator


def foldr(function, list, initial):
    accumulator = initial
    i = length(list) - 1
    while i >= 0:
        accumulator = function(accumulator, list[i])
        i = i - 1
    return accumulator


def reverse(list):
    result = []
    i = length(list) - 1
    while i >= 0:
        result = result + [list[i]]
        i = i - 1
    return result
