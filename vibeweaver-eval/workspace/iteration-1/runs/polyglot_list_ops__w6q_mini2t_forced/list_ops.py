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


def filter(function, lst):
    result = []
    for item in lst:
        if function(item):
            result.append(item)
    return result


def length(lst):
    count = 0
    for _ in lst:
        count += 1
    return count


def map(function, lst):
    result = []
    for item in lst:
        result.append(function(item))
    return result


def foldl(function, lst, initial):
    result = initial
    for el in lst:
        result = function(result, el)
    return result


def foldr(function, lst, initial):
    result = initial
    for i in range(len(lst) - 1, -1, -1):
        result = function(result, lst[i])
    return result


def reverse(lst):
    result = []
    for i in range(len(lst) - 1, -1, -1):
        result.append(lst[i])
    return result
