def append(list1, list2):
    return concat([list1, list2])


def concat(lists):
    return [element for items in lists for element in items]


def filter(function, list):
    return [item for item in list if function(item)]


def length(list):
    return sum(1 for _ in list)


def map(function, list):
    return [function(element) for element in list]


def foldl(function, list, initial):
    acc = initial
    for item in list:
        acc = function(acc, item)
    return acc


def foldr(function, list, initial):
    acc = initial
    for item in list[::-1]:
        acc = function(acc, item)
    return acc


def reverse(list):
    return list[::-1]
