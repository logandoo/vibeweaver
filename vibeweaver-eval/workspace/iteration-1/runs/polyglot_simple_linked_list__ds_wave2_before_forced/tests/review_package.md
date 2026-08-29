# A4.9 Review Package — polyglot_simple_linked_list

## git log BASE..HEAD
44a8187 backup: before changes
44a8187 backup: before changes

## git diff --stat 83af3ee..<worktree>
 .../run.log                                        | 117 +++++++++++++++++++++
 .../simple_linked_list.py                          |  41 ++++++--
 2 files changed, 148 insertions(+), 10 deletions(-)

## git diff -U10 (stub -> implementation)
diff --git a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_simple_linked_list__ds_wave2_before_forced/simple_linked_list.py b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_simple_linked_list__ds_wave2_before_forced/simple_linked_list.py
index dfb9e6c..993b384 100644
--- a/vibeweaver-eval/workspace/iteration-1/runs/polyglot_simple_linked_list__ds_wave2_before_forced/simple_linked_list.py
+++ b/vibeweaver-eval/workspace/iteration-1/runs/polyglot_simple_linked_list__ds_wave2_before_forced/simple_linked_list.py
@@ -1,36 +1,57 @@
 class EmptyListException(Exception):
     pass
 
 
 class Node:
     def __init__(self, value):
-        pass
+        self._value = value
+        self._next = None
 
     def value(self):
-        pass
+        return self._value
 
     def next(self):
-        pass
+        return self._next
 
 
 class LinkedList:
     def __init__(self, values=None):
-        pass
+        self._head = None
+        self._length = 0
+        if values is not None:
+            for value in values:
+                self.push(value)
 
     def __iter__(self):
-        pass
+        current = self._head
+        while current is not None:
+            yield current.value()
+            current = current.next()
 
     def __len__(self):
-        pass
+        return self._length
 
     def head(self):
-        pass
+        if self._head is None:
+            raise EmptyListException("The list is empty.")
+        return self._head
 
     def push(self, value):
-        pass
+        node = Node(value)
+        node._next = self._head
+        self._head = node
+        self._length += 1
 
     def pop(self):
-        pass
+        if self._head is None:
+            raise EmptyListException("The list is empty.")
+        value = self._head.value()
+        self._head = self._head.next()
+        self._length -= 1
+        return value
 
     def reversed(self):
-        pass
+        result = LinkedList()
+        for value in self:
+            result.push(value)
+        return result
