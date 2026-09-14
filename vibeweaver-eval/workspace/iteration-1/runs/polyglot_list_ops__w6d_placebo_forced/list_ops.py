def append(list1, list2):
    result = []
    for item in list1:
        result += [item]
    for item in list2:
        result += [item]
    return result


def concat(lists):
    result = []
    for each in lists:
        for item in each:
            result += [item]
    return result


def filter(function, list):
    result = []
    for item in list:
        if function(item):
            result += [item]
    return result


def length(list):
    count = 0
    for _ in list:
        count += 1
    return count


def map(function, list):
    result = []
    for item in list:
        result += [function(item)]
    return result


def foldl(function, list, initial):
    accumulator = initial
    for item in list:
        accumulator = function(accumulator, item)
    return accumulator


def foldr(function, list, initial):
    accumulator = initial
    for item in reverse(list):
        accumulator = function(item, accumulator)
    return accumulator


def reverse(list):
    result = []
    for item in list:
        result = [item] + result
    return result
