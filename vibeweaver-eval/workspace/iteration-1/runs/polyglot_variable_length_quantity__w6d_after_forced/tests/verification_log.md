- iter 1 PASS/FAIL: criteria #1-#8 | diagnosis: initial run on implementation
Criterion 1+6: prompt examples (encode + round-trip decode)
  [PASS] 0x00000000 -> ['0x0']
  [PASS] 0x00000040 -> ['0x40']
  [PASS] 0x0000007f -> ['0x7f']
  [PASS] 0x00000080 -> ['0x81', '0x0']
  [PASS] 0x00002000 -> ['0xc0', '0x0']
  [PASS] 0x00003fff -> ['0xff', '0x7f']
  [PASS] 0x00004000 -> ['0x81', '0x80', '0x0']
  [PASS] 0x00100000 -> ['0xc0', '0x80', '0x0']
  [PASS] 0x001fffff -> ['0xff', '0xff', '0x7f']
  [PASS] 0x00200000 -> ['0x81', '0x80', '0x80', '0x0']
  [PASS] 0x08000000 -> ['0xc0', '0x80', '0x80', '0x0']
  [PASS] 0x0fffffff -> ['0xff', '0xff', '0xff', '0x7f']
Criterion 2: encode([]) == []
  [PASS] encode([])
Criterion 4: decode([]) == []
  [PASS] decode([])
Criterion 3: multiple values
  [PASS] encode([0x7F, 0x2000])
  [PASS] decode([0x7F, 0xC0, 0x00])
Criterion 7: 0xFFFFFFFF
  [PASS] encode([0xFFFFFFFF])
  [PASS] decode([0x8F,0xFF,0xFF,0xFF,0x7F])
Criterion 5: incomplete sequence raises ValueError
  [PASS] decode(['0xff']) raises
  [PASS] decode(['0x80']) raises
  [PASS] decode(['0xc0']) raises
  [PASS] decode(['0x81', '0x80']) raises
  [PASS] decode(['0x7f', '0xff']) raises
Criterion 3: exhaustive round-trip 0..2**20-1
  [PASS] exhaustive 0..1048575
Criterion 8: import / runtime errors
  [PASS] module imported and ran

- iter 1 PASS: criteria #1-#8 all pass

ALL CHECKS PASSED

- iter 1 final fresh run on delivered tree: PASS (re-ran prompt examples + 0xFFFFFFFF + incomplete-sequence ValueError + exhaustive 0..2**20-1)
FRESH RUN: ALL CHECKS PASSED
