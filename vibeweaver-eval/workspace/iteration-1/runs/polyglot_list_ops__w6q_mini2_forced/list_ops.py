def append(list1, list2):
    result = []
    for i in range(length(list1)):
        result = result + [list1[i]]
    for i in range(length(list2)):
        result = result + [list2[i]]
    return result


def concat(lists):
    result = []
    for i in range(length(lists)):
        sublist = lists[i]
        for j in range(length(sublist)):
            result = result + [sublist[j]]
    return result


def filter(function, list):
    result = []
    for i in range(length(list)):
        if function(list[i]):
            result = result + [list[i]]
    return result


def length(list):
    count = 0
    for _ in list:
        count = count + 1
    return count


def map(function, list):
    result = []
    for i in range(length(list)):
        result = result + [function(list[i])]
    return result


def foldl(function, list, initial):
    acc = initial
    for i in range(length(list)):
        acc = function(acc, list[i])
    return acc


def foldr(function, list, initial):
    acc = initial
    reversed_list = reverse(list)
    for i in range(length(reversed_list)):
        acc = function(acc, reversed_list[i])
    return acc


def reverse(list):
    result = []
    for i in range(length(list) - 1, -1, -1):
        result = result + [list[i]]
    return result
