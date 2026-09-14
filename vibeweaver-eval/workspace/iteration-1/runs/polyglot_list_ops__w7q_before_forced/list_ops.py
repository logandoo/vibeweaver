def append(list1, list2):
    result = []
    for item in list1:
        result.append(item)
    for item in list2:
        result.append(item)
    return result


def concat(lists):
    result = []
    for lst in lists:
        for item in lst:
            result.append(item)
    return result


def filter(function, list):
    result = []
    for item in list:
        if function(item):
            result.append(item)
    return result


def length(list):
    count = 0
    for _ in list:
        count += 1
    return count


def map(function, list):
    result = []
    for item in list:
        result.append(function(item))
    return result


def foldl(function, list, initial):
    accumulator = initial
    for item in list:
        accumulator = function(accumulator, item)
    return accumulator


def foldr(function, list, initial):
    accumulator = initial
    reversed_list = []
    for item in list:
        reversed_list.append(item)
    i = length(reversed_list) - 1
    while i >= 0:
        accumulator = function(accumulator, reversed_list[i])
        i -= 1
    return accumulator


def reverse(list):
    result = []
    for item in list:
        result.append(item)
    i = length(result) - 1
    new_list = []
    while i >= 0:
        new_list.append(result[i])
        i -= 1
    return new_list
