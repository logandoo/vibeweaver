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
    for item in list:
        count += 1
    return count


def map(function, list):
    result = []
    for item in list:
        result.append(function(item))
    return result


def foldl(function, list, initial):
    acc = initial
    for item in list:
        acc = function(acc, item)
    return acc


def foldr(function, list, initial):
    acc = initial
    i = length(list) - 1
    while i >= 0:
        acc = function(list[i], acc)
        i -= 1
    return acc


def reverse(list):
    result = []
    i = length(list) - 1
    while i >= 0:
        result.append(list[i])
        i -= 1
    return result
