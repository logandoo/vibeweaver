> cap=5  stall=3×
1. "+1 (613)-995-0253" -> number == "6139950253"
2. "613-995-0253" -> number == "6139950253"
3. "1 613 995 0253" -> number == "6139950253"
4. "613.995.0253" -> number == "6139950253"
5. "(223) 456-7890" -> number == "2234567890"
6. "223.456.7890" -> number == "2234567890"
7. "223 456   7890   " -> number == "2234567890"
8. 9 digits -> ValueError("must not be fewer than 10 digits")
9. 11 digits not starting with 1 -> ValueError("11 digits must start with 1")
10. "12234567890" -> number == "2234567890"
11. "+1 (223) 456-7890" -> number == "2234567890"
12. more than 11 digits -> ValueError("must not be greater than 11 digits")
13. letters present -> ValueError("letters not permitted")
14. punctuation present -> ValueError("punctuations not permitted")
15. area code starts with 0 -> ValueError("area code cannot start with zero")
16. area code starts with 1 -> ValueError("area code cannot start with one")
17. exchange code starts with 0 -> ValueError("exchange code cannot start with zero")
18. exchange code starts with 1 -> ValueError("exchange code cannot start with one")
19. area_code attribute for "2234567890" == "223"
20. pretty() for "2234567890" == "(223)-456-7890"
21. pretty() for "12234567890" == "(223)-456-7890"
