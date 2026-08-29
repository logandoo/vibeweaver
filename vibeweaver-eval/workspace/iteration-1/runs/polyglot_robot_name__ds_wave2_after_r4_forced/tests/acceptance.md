> cap=5  stall=3×
1. Robot().name matches regex ^[A-Z]{2}\d{3}$ (two uppercase letters + three digits).
2. name sticks: repeated access returns the same name.
3. Different robots have different names.
4. reset() wipes the name; next access returns a new, format-valid name.
5. Reset-after-reseed (canonical seeded test) yields a DIFFERENT name from the original.
6. Every robot among N simultaneously-existing robots has a unique name.
7. robot_name.py imports cleanly with no syntax/runtime errors.
