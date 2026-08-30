1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them - don't pick silently.
If a simpler approach exists, say so. Push back when warranted.
If something is unclear, stop. Name what's confusing. Ask.
If the project has memory/MEMORY.md, check ⛔ Forbidden Approaches and ✅ Verified Fixes for files you're about to touch — don't reintroduce previously fixed bugs or retry failed approaches.

2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
No error handling for impossible scenarios.
If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:

Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:

Remove imports/variables/functions that YOUR changes made unused.
Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

"Add validation" → "Write tests for invalid inputs, then make them pass"
"Fix the bug" → "Write a test that reproduces it, then make it pass"
"Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## Reviewer Smell Baseline (per-diff checklist)

Consumed by §A4.9 independent reviews (TESTING_PROTOCOLS.md) and by
self-review before dispatch. Baseline adapted from Fowler, *Refactoring*,
ch.3. Match each smell against the diff; two binding rules:

1. **The repo overrides.** A documented repo standard always wins; where it
   endorses something this baseline would flag, suppress the smell.
2. **Always a judgement call.** Each smell is a labelled heuristic
   ("possible Feature Envy"), never a hard violation. Skip anything tooling
   already enforces.

- **Mysterious Name** — a name that doesn't reveal what it does or holds →
  rename it; if no honest name comes, the design is murky.
- **Duplicated Code** — the same logic shape in more than one hunk or file →
  extract the shared shape; call it from both.
- **Feature Envy** — a method reaching into another object's data more than
  its own → move the method onto the data it envies.
- **Data Clumps** — the same fields/params travelling together → bundle into
  one type; pass that.
- **Primitive Obsession** — a primitive standing in for a domain concept →
  give the concept its own small type.
- **Repeated Switches** — the same switch/if-cascade on the same type recurs →
  polymorphism, or one map both sites share.
- **Shotgun Surgery** — one logical change forces scattered edits → gather
  what changes together into one module.
- **Divergent Change** — one module edited for several unrelated reasons →
  split so each module changes for one reason.
- **Speculative Generality** — abstraction for needs the spec doesn't have →
  delete it; inline back until a real need shows.
- **Message Chains** — long `a.b().c().d()` navigation → hide the walk behind
  one method on the first object.
- **Middle Man** — a function that mostly delegates onward → cut it; call the
  real target directly.
- **Refused Bequest** — a subclass ignoring/overriding most of what it
  inherits → drop the inheritance; use composition.