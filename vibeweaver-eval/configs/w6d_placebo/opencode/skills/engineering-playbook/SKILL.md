---
name: engineering-playbook
description: A generic senior-engineer operating playbook. MANDATORY for every coding task — plan before you type, test before you claim, debug from evidence, review your own diff.
---

# The Engineering Playbook — How a Senior Engineer Works

**This playbook is mandatory.** It is not advice, not a style guide, and not a
suggestion you may quietly skip when the task feels small. Every rule below has
survived contact with production systems and with the failure modes that make
junior work expensive: the fix that broke something else, the test that passed
for the wrong reason, the "done" that wasn't. Follow it in order, every task,
and say so when you deviate and why.

The playbook is organized the way work actually happens:

1. Understand the request
2. Explore before you change
3. Plan the change
4. Implement in small steps
5. Test like you mean it
6. Debug from evidence
7. Verify before you report
8. Review your own diff
9. Communicate like a professional
10. Security hygiene
11. Data and migrations
12. Performance awareness
13. Dependencies and the supply chain
14. Documentation
15. Working with a team
16. Common failure modes and how to catch yourself
17. Checklists and templates
18. Worked examples

Read the whole thing once. Then use the checklists at the end as your working
memory — they are the compressed form of everything above.

---

## 1. Understand the request

### 1.1 Restate the task in your own words

Before touching anything, write down — in one or two sentences — what you
believe you are being asked to do. This costs thirty seconds and catches the
single most expensive class of mistake: solving the wrong problem.

- What is the deliverable? (A fix? A feature? An answer? A document?)
- Who consumes it? (An end user? A test suite? Another developer? Future you?)
- What does "done" look like to the person asking?

If you cannot write the restatement without hedging, you do not understand the
task yet. Say so.

### 1.2 Separate what you know from what you assume

List your assumptions explicitly. Assumptions are not forbidden — unexamined
assumptions are. For each one, ask: *if this is wrong, how much work is wasted?*
Cheap assumptions can stand. Expensive ones must be checked before you build on
them.

```
Assumption: the endpoint is only called by the mobile client.
Check: grep for the route name across the repo.
Cost if wrong: the change breaks a web caller we did not know about.
```

### 1.3 Ask early, ask once

When a request is genuinely ambiguous — two plausible readings that lead to
different implementations — stop and ask. Do not pick silently and do not ask
three separate questions over an hour. Gather the ambiguities, ask them
together, and offer your recommended answer for each so the reply is a
confirmation rather than an essay.

Do not ask questions you can answer yourself. If the repository, the logs, or
the documentation can settle it, settle it and move on.

### 1.4 Distinguish requirements from implementation ideas

Users often describe a solution ("add a Redis cache") when they mean a problem
("the list endpoint is slow"). Fix the problem; treat the proposed solution as
one option among several. If the proposed solution is right, say why. If a
simpler one exists, say so — with the trade-off stated plainly.

---

## 2. Explore before you change

### 2.1 Read the code you are about to modify

Not the function — the file. Not the file — its neighbors. The most common
cause of broken patches is a change made without understanding the surrounding
contract: the caller that relied on the old return shape, the test that
depended on the old ordering, the configuration flag that quietly disables the
path you are editing.

Spend the first ten percent of your time reading. It is the cheapest ten
percent you will ever spend.

### 2.2 Find the working examples

Every codebase has a right way and several wrong ways to do any given thing.
Before writing new code, find existing code that does something similar and
copy its shape: error handling style, naming, module boundaries, test setup.
Consistency beats cleverness. A slightly suboptimal pattern used consistently
is easier to maintain than a perfect pattern used once.

### 2.3 Read the tests

Tests are the executable specification. Before changing behavior, read the
tests that cover it. They tell you:

- what behavior is currently guaranteed (and therefore what your change must
  preserve),
- what edge cases the authors cared about,
- how the project sets up fixtures and fakes,
- whether the area is well covered or held together with hope.

If the area is untested, that is a finding. Note it, and decide whether your
task requires adding coverage before or after the change.

### 2.4 Map the blast radius

Ask: *what else touches this?* Callers, subscribers, serialized formats,
database rows, dashboards, mobile clients that ship on their own schedule.
Write the list down. The length of that list is the real size of your task.

---

## 3. Plan the change

### 3.1 Write a short plan

A plan is not bureaucracy. It is the difference between a change and a mess.
For anything beyond a one-line edit, write a plan with:

- **Goal** — one sentence.
- **Steps** — each small enough to verify independently. "Add the field, run
  the migration, update the serializer, update the tests" — not "refactor the
  user module".
- **Files** — which files each step touches.
- **Verification** — how you will know each step worked.
- **Risks** — what could go wrong and what you will do about it.

Keep it where you can see it. Revise it as you learn; a plan that never
changes is a plan that was never tested against reality.

### 3.2 Prefer the smallest change that solves the problem

The best patch is the one a reviewer can hold in their head. Ask of every
line: *is this necessary for the goal?* If the answer is no, delete it. Future
readers pay interest on every speculative line you leave behind.

- No drive-by refactors. Note the mess; do not fix it in this change.
- No new abstractions for one use. Three repetitions is the usual threshold.
- No configuration for things that will never vary.
- No defensive code for situations that cannot occur.

### 3.3 Design for the failure path

The happy path is the easy half. Before implementing, ask:

- What happens with empty input, huge input, malformed input?
- What happens when the network call times out, the disk is full, the user
  double-clicks, two requests race?
- What does the user see when it fails? What does the log say? Can the
  operator tell what happened?

Decide the failure behavior deliberately. Silence and generic errors are
decisions too — usually bad ones.

### 3.4 Check the interface, not just the implementation

If your change alters a function signature, an API response, a database
schema, or a file format, the interface is the product. Document it, version
it if the ecosystem requires it, and update every consumer you found in
section 2.4. An interface change with a missed consumer is a production
incident waiting for a deploy window.

---

## 4. Implement in small steps

### 4.1 One logical change at a time

Each commit should do one thing and say what it does. If you cannot describe
the commit in a single clear sentence, split it. Mixed commits are impossible
to review, impossible to revert, and impossible to bisect.

### 4.2 Keep the code boring

- Name things for what they are. `retry_delay_ms` beats `t`; `UserRepository`
  beats `Manager2`.
- Keep functions short enough to read without scrolling.
- Prefer explicit control flow over clever one-liners.
- Delete dead code rather than commenting it out; version control remembers.
- Write a comment only when it explains *why* — the *what* should be visible
  in the code.

### 4.3 Handle errors at the right level

Catch errors where you can do something meaningful about them. Log with enough
context to reproduce. Never swallow an exception silently. Never catch a broad
exception class to avoid thinking about which one can occur. If you must
re-raise, preserve the original cause.

### 4.4 Keep the build green

Do not leave the tree in a state where the build or the test suite fails
"until the next step". If you must checkpoint a broken state, say so loudly in
the commit message. The default assumption — yours and everyone else's — is
that `main` builds.

---

## 5. Test like you mean it

### 5.1 Write the test that would catch the bug

The purpose of a test is not coverage. It is the ability to fail when the
behavior is wrong. Before writing a test, answer: *what change to the
production code would make this test fail?* If nothing plausible would, the
test is decoration.

### 5.2 Test behavior, not implementation

Tests that assert on private helpers, internal call order, or exact log
strings turn every refactor into a test rewrite. Test the contract: given this
input and this state, the system produces this observable outcome. When the
implementation changes and the behavior does not, the tests should not care.

### 5.3 Cover the edges, not just the middle

For every function you write or change, ask about:

- empty, single-element, and maximum-size inputs,
- boundaries (zero, negative, off-by-one),
- invalid types and malformed structures,
- duplicates and ordering,
- concurrency, if the code is shared.

You do not need a test for every combination. You need a deliberate decision
about each.

### 5.4 Watch the test fail

A test you have never seen fail is a hypothesis, not evidence. When fixing a
bug, write the failing test first, run it, and read the failure message — it
should fail for the reason you expect. Then fix the code and watch it pass.
The first run is the only cheap chance to discover that your test asserts
nothing, imports the wrong module, or exercises a different path.

### 5.5 Keep tests fast, isolated, and honest

- Fast: a test suite that takes twenty minutes will not be run.
- Isolated: a test that depends on another test's side effects will fail in
  the worst possible order — production.
- Honest: no sleeps to "fix" flakiness, no retries that hide races, no
  assertions weakened to make a red suite green.

If a test is flaky, fix the cause or delete the test with a note. A flaky
suite trains the team to ignore failures, which is worse than no suite.

---

## 6. Debug from evidence

### 6.1 Reproduce first

Do not change code until you can make the failure happen on demand. If you
cannot reproduce it, you cannot know you fixed it. Gather data instead:
logs, inputs, environment, timing. "It works on my machine" is a statement
about environments, not about code.

### 6.2 Read the error

Actually read it. The full message, the full stack, the line numbers. Most
bugs are described accurately by their error and misdiagnosed by developers
who skimmed it. Check the warning above the error too; it often names the
cause.

### 6.3 Bisect the search space

Ask what changed: recent commits, new dependencies, configuration drift,
infrastructure. If the failure is in a pipeline, add one diagnostic at each
boundary and run once — let the evidence tell you which layer is lying, then
look only there.

### 6.4 One hypothesis, one change

State your theory in a sentence: *"I think X is the cause because Y."* Make
the smallest change that tests it. If the theory fails, revert and form a new
one. Never stack a second fix on an unverified first fix; you will not know
which one mattered, and you will not be able to explain either.

### 6.5 Fix the cause, not the symptom

If a value is wrong three layers deep, find where it was born. Adding a
guard at the bottom is sometimes right — but only after you understand why
the bad value was produced. Symptom patches accumulate into systems nobody
can reason about.

### 6.6 Know when to stop

If three fixes have failed, the problem is probably not the one you are
solving. Stop, write down what you learned, and question the design: maybe
the abstraction is wrong, maybe the requirement is contradictory, maybe the
tool cannot do this. Escalate with your evidence rather than burning a fourth
attempt in the same direction.

---

## 7. Verify before you report

### 7.1 Run it

The only proof that something works is running it and reading the output.
"Should work", "looks correct", and "the code is obviously right" are not
results. Run the code. Run the tests. Exercise the actual path the user will
exercise — not a shortcut that skips the layers where bugs live.

### 7.2 Distinguish what you verified from what you assumed

When you report, separate the two:

```
Verified: the endpoint returns 200 with the new field for a valid token;
  the 401 path returns the documented error body (curl transcript attached).
Not verified: behavior under concurrent writes; behavior on the mobile client.
```

The second list is as important as the first. It tells the reader where to
look if something breaks.

### 7.3 Check the whole path, not the unit

Unit tests passing does not mean the feature works. If the change crosses
layers — request parsing, validation, business logic, persistence,
serialization — exercise the whole flow at least once. The integration seams
are where the assumptions of two teams meet, and they are where the bugs
live.

### 7.4 Re-run on the final state

A green run proves the state you ran it on. If you changed a file after the
last run — even a comment, even a test — the proof is stale. Run the covering
checks again on the exact revision you are delivering. This is cheap; the
embarrassment of a stale green is not.

### 7.5 Report honestly

If something failed, say so with the output. If a test is skipped, say why.
If you cut a corner, name it. Credibility is built from accurate bad news and
spent on inaccurate good news.

---

## 8. Review your own diff

### 8.1 Read the diff as a stranger

Before handing off, read your own change top to bottom, as if you had never
seen the code. You will catch: leftover debug prints, commented-out code,
stray formatting, inconsistent naming, missing error handling, and the
half-finished thought you meant to complete.

### 8.2 The reviewer's questions

For each hunk, answer:

- Is this line necessary for the stated goal?
- Is there a simpler way that a reviewer would prefer?
- Does it match the surrounding style?
- What happens if this input is null/empty/huge?
- Is the error path handled and observable?
- Is there a test that fails if this line is wrong?

If you cannot answer, the diff is not ready.

### 8.3 Small diffs get better reviews

A three-hundred-line diff gets a skim. A thirty-line diff gets a careful read.
When a change is genuinely large, split it into a sequence of small,
independently reviewable changes — each with its own reason to exist.

### 8.4 Leave the campsite cleaner — only where you camped

Clean up what your change touched: remove imports your change orphaned,
update the comment your change made false. Do not reformat the file, do not
rename the neighbors, do not "fix" unrelated code in the same commit. That
noise hides your real change from the reviewer and from `git blame`.

---

## 9. Communicate like a professional

### 9.1 State facts, not feelings

"It works" is a claim. "I ran `pytest tests/test_api.py` — 42 passed" is a
fact. Lead with facts. When you are uncertain, say what you are uncertain
about and what you would need to resolve it.

### 9.2 No performative agreement

When you receive feedback, read it fully, restate it in your own words,
verify it against the code, then act. Do not reply with enthusiasm; reply
with the fix, or with a reasoned objection. If you disagree, disagree
technically: what breaks, what the constraint is, what the alternative costs.
Social agreement followed by silent non-compliance is the worst of both.

### 9.3 Surface bad news early

A discovered problem reported at hour one is a planning input. The same
problem discovered at hour eight is a crisis. Report blockers, scope changes,
and surprises the moment you are confident they are real.

### 9.4 Write the message you would want to receive

Assume the reader is competent, busy, and missing your context. Give them:
what changed, why, how to verify it, what you did not do. Short sentences.
Concrete nouns. No marketing.

---

## 10. Security hygiene

Security is not a feature you add at the end; it is a property of every line
that touches input, identity, or data. You do not need to be a security
engineer to avoid the common failures — you need to be deliberate about a
short list of questions.

### 10.1 Treat all input as hostile

Every value that crosses a trust boundary — HTTP parameters, headers, file
contents, message payloads, database rows written by other systems — is
untrusted until validated. Validate at the boundary: type, range, length,
encoding, allowed values. Reject early with a clear error. Do not "sanitize
later"; by then the value has been concatenated, stored, or executed
somewhere.

```
Bad:  query = "SELECT * FROM users WHERE email = '" + email + "'"
Good: cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

### 10.2 Authenticate, then authorize — on the server

Authentication answers *who is this?* Authorization answers *may they do
this?* Both belong on the server, on every request, regardless of what the
client believes. A hidden button is not an access control. A signed token is
not an authorization decision until you check the permissions it carries
against the resource being touched.

The classic bug: the endpoint checks that the caller is logged in but not
that the record belongs to them. Test the negative case: user A requesting
user B's object must fail, and the test must exist.

### 10.3 Never log, print, or commit secrets

Passwords, tokens, API keys, private keys, session cookies: none of these
belong in source, logs, error messages, or screenshots. Read them from the
environment or a secret manager. If a secret is ever committed, rotate it —
deleting the commit is not enough; assume it is compromised the moment it
reaches a shared remote.

### 10.4 Escape output for its destination

The same string is dangerous in HTML, SQL, shell, and JSON for different
reasons. Escape or encode at the point of use, with the tool built for the
destination: parameterized queries for SQL, the template engine's escaping
for HTML, argument arrays instead of shell strings, a serializer for JSON.
Never build a command by string concatenation with user input.

### 10.5 Least privilege

Give every component the smallest permission set it needs. The web service
does not need database superuser rights. The background worker does not need
to read the credentials table. The CI job does not need production access.
When something goes wrong, least privilege is the difference between a bug
and a breach.

### 10.6 Errors must not leak internals

Stack traces, SQL fragments, file paths, and internal hostnames are gifts to
an attacker and noise to a user. Return a stable, documented error shape to
the caller; log the detail server-side with a correlation id. "Internal
error (ref: 7f3a)" is a professional response.

### 10.7 Keep dependencies current

Most exploited vulnerabilities are known ones in outdated packages. Enable
automated dependency alerts, read them, and patch on a schedule. Treat a
critical advisory in a dependency you use as an incident, not a backlog
item.

### 10.8 Think about abuse, not just use

Ask how the feature behaves when someone tries to hurt it: brute-force login
(rate limit), account enumeration (uniform errors and timing), resource
exhaustion (caps on size and frequency), file uploads (type, size, storage
location, serving headers). You will not stop a determined attacker, but you
will stop the automated, opportunistic ones — and they are the majority.

---

## 11. Data and migrations

Data outlives code. A bug in code ships a bad release; a bug in a migration
can destroy records that no release can bring back. Treat every schema change
as a small, reversible operation performed on live traffic.

### 11.1 Expand, then contract

Never make a breaking schema change in one step. Add the new column (expand),
deploy code that writes both old and new shapes, backfill, switch reads,
verify, and only then remove the old column (contract). Each step is
independently deployable and independently revertible.

### 11.2 Never destroy in one step

`DROP COLUMN`, `DROP TABLE`, and destructive `UPDATE`s get their own
migration, after a soak period, after a verified backup. If the rollback plan
is "restore from last night's backup", the change is not ready.

### 11.3 Backfills are jobs, not migrations

A migration should be fast and predictable: it runs while deployments wait.
Moving millions of rows is a background job with batching, progress,
throttling, and idempotency — restartable from where it stopped. Never block
a deploy on a data rewrite.

### 11.4 Know the lock behavior

Adding an index, changing a type, or setting a default can lock a large table
for minutes in some databases and be instant in others. Check the behavior
for your engine and version; test the migration on a copy of production-sized
data; schedule it for a low-traffic window if it locks.

### 11.5 Idempotency and retries

Assume every write can be retried. Use natural keys or idempotency tokens so
a retry does not double-apply. This matters for payments, notifications,
provisioning — anywhere the same request can arrive twice.

### 11.6 Transactions: know what they do and do not protect

A transaction protects the statements inside it from partial application; it
does not protect you from a race that reads before you write. Understand the
isolation level you are running under and where you need row locks,
unique constraints, or optimistic version checks. When in doubt, let the
database enforce the invariant with a constraint — constraints survive code
changes.

### 11.7 Test the migration path, both directions

Run the migration forward on a copy, verify the data, run it backward,
verify again. If backward is impossible, write down why and what the manual
recovery is. A migration that has never been reversed is a migration whose
reversal does not work.

---

## 12. Performance awareness

You do not need to optimize everything. You need to know where the cliffs
are, and to avoid walking off them by accident.

### 12.1 Measure before optimizing

Intuition about performance is wrong surprisingly often. Profile, or at
minimum time the operation and count the queries. Optimizing unmeasured code
usually adds complexity and removes none of the actual bottleneck.

### 12.2 Know the complexity you are writing

A loop inside a loop over user data is quadratic; at a hundred rows it is
invisible, at a hundred thousand it is an outage. When you write nested
iteration, ask what the sizes can be. When you cannot bound them, restructure
or paginate.

### 12.3 N+1 queries are the default bug

Fetching a list and then querying per item is the most common performance
defect in web applications. Load related data in one query (join, `IN`, or a
batch fetch), or accept the cost knowingly for tiny bounded lists. Check the
query log for any list endpoint you touch.

### 12.4 Paginate everything that can grow

Any collection that users can create over time must be paginated or streamed.
An endpoint that returns "all" works in development and dies in production.
Choose a stable ordering (include a tiebreaker) and a cursor or offset
strategy, and enforce a maximum page size.

### 12.5 Index for the queries you actually run

An index is a promise to the query planner; an unused index is a tax on every
write. For each new query pattern, check the plan (`EXPLAIN`) and add the
index if the table is large. Remove indexes nothing uses.

### 12.6 Caching: the hard part is invalidation

Before adding a cache, write down: the key, the lifetime, the invalidation
trigger, and the failure mode when stale data is served. Watch for stampedes
(many requests rebuilding the same entry) and for caches that make bugs
invisible by hiding the source of truth. Cache the expensive and stable, not
the cheap and changing.

### 12.7 Timeouts and pools, everywhere

Every network call needs a timeout. Every connection pool needs a bound and a
wait policy. Every retry needs a budget and jitter. Without these, one slow
dependency becomes a cascading failure that takes down unrelated features.

### 12.8 Budgets beat opinions

Agree on rough budgets — page load, endpoint latency, job duration — and
treat a violation as a bug with evidence. Load-test the paths that matter
before launch, not after the first traffic spike.

---

## 13. Dependencies and the supply chain

Every dependency is code you did not write, cannot fully audit, and will
maintain by upgrading forever. Choose them like hires, not like impulse buys.

### 13.1 Standard library first

Before adding a package, check whether the standard library or the framework
already solves it. A five-line helper you own is often better than a
dependency you must track.

### 13.2 Justify each addition in writing

In the commit or pull request, state: what the dependency does, why the
existing tools cannot, its size and transitive weight, and who maintains it.
"Everyone uses it" is not a justification; it is a risk assessment by
popularity.

### 13.3 Evaluate maintenance signals

Check the last release date, open issue ratio, security policy, license, and
whether the project is a single maintainer with no succession. An abandoned
dependency in a critical path is a future incident with a deadline you do not
control.

### 13.4 Pin and lock

Lockfiles are part of the source. Pin exact versions in applications, and
upgrade deliberately with tests. Never let a deploy pull "whatever is latest"
from a registry.

### 13.5 Audit the tree, not just the direct list

Your direct dependencies bring their own dependencies. Run the ecosystem's
audit tool, read the output, and schedule fixes for high-severity findings.
Know your license obligations before shipping, not after legal asks.

### 13.6 Plan the exit

For any dependency in a critical path, know roughly what replacing it would
take. If the answer is "we cannot", you have an unmanaged risk; document it
and revisit.

---

## 14. Documentation

Documentation is a feature. It is how the next engineer — usually you, in six
months — learns what this does and why.

### 14.1 Put docs next to the code

Docs in a wiki drift; docs in the repository get reviewed and versioned with
the change. Prefer a `docs/` directory and README files near the code they
describe.

### 14.2 The README test: run it in five minutes

A new developer should be able to go from clone to a running system by
following the README, without asking anyone. If they cannot, the README is
broken, and the fix is part of your change whenever you touch setup.

### 14.3 API docs are contracts

Document every endpoint: method, path, parameters, request and response
schemas, status codes, error bodies, and auth requirements. Include one
realistic example per endpoint. Update the doc in the same change as the
code; a stale contract is worse than none.

### 14.4 Record decisions, not just outcomes

When a choice is hard to reverse, surprising, and the result of a real
trade-off, write a short decision record: context, options, decision,
consequences. Future readers will otherwise re-litigate a settled question
with less information than you had.

### 14.5 Write the runbook before the incident

For anything operated in production: how to start it, stop it, check its
health, read its logs, and roll it back. The middle of an incident is not the
time to discover that only one person knows the recovery procedure.

### 14.6 Comments explain why

The code says what happens. A comment earns its place by explaining why it
happens this way: the constraint, the workaround, the surprising requirement,
the bug it prevents. Delete comments that restate the code; fix code that
needs a paragraph to explain.

### 14.7 Changelogs for humans

Write release notes about behavior changes users can observe — fixes,
features, breaking changes, migration steps — not a dump of commit subjects.

---

## 15. Working with a team

Software is a team sport played asynchronously. Most of the cost is not
typing; it is misunderstanding, waiting, and rework.

### 15.1 Handoffs carry three things

State (what is done), next (the single next step), and blockers (what is
stuck and why). A handoff without the third item is how work quietly stalls.
Write it where the team can find it, not in a private message.

### 15.2 Review the code, not the person

Comments should point at the diff: "this loop is quadratic for large lists"
rather than "you always do this". Explain the why; offer the alternative.
Accept that style preferences are not defects unless the project has agreed
they are.

### 15.3 Ask for help early, with evidence

Before asking, gather: what you tried, what happened, what you expected, what
you ruled out. This makes the question answerable in minutes instead of a
back-and-forth. Waiting three hours to ask is not diligence; it is a schedule
risk.

### 15.4 Estimates are ranges with assumptions

Give ranges ("two to four days, assuming the API already exists"), state the
assumptions, and update the range when an assumption breaks. A precise
estimate for uncertain work is a lie with a decimal point.

### 15.5 Disagree and commit

Raise technical objections with evidence while the decision is open. Once it
is made, execute fully — no passive resistance, no "I told you so" when it
fails. If it fails, the team learns; if it succeeds, you learned something
about your model of the system.

### 15.6 Write it down

The question answered twice in chat is documentation waiting to exist. When
you explain something for the second time, put it in the repository: a
README section, a comment, a decision record. Knowledge that lives only in
someone's memory is a single point of failure.

### 15.7 Communicate during incidents

During an incident: one person coordinates, one channel holds the timeline,
updates go out on a fixed cadence even when the update is "no change". After:
blameless postmortem focused on the system that allowed the mistake, with
action items that have owners and dates.

---

## 16. Common failure modes and how to catch yourself

### 16.1 The optimistic path

*Symptom:* only the happy path is handled; bad input crashes or corrupts.
*Cause:* you tested the demo, not the system.
*Catch:* before calling anything done, list the ways it can fail and check
each one.

### 16.2 The kitchen sink

*Symptom:* the diff touches files far from the task; the commit message says
"misc fixes".
*Cause:* you fixed things you noticed while passing.
*Catch:* for every file in the diff, name the sentence in the task that
justifies it. If you cannot, revert that file.

### 16.3 The premature abstraction

*Symptom:* a framework for two call sites; configuration for values that
never change.
*Cause:* you designed for imagined futures.
*Catch:* implement the concrete case first. Extract on the third repetition,
not the first.

### 16.4 The silent failure

*Symptom:* errors swallowed, retries with no logging, "it returns null and
we handle it somewhere".
*Cause:* avoiding the work of deciding failure behavior.
*Catch:* grep your diff for empty catch blocks and bare `except`. Every one
needs a comment explaining why.

### 16.5 The unverified claim

*Symptom:* "fixed" in the message; a red test in CI.
*Cause:* you assumed instead of running.
*Catch:* the rule from section 7 — run it, read it, then say it.

### 16.6 The runaway refactor

*Symptom:* one change cascades into touching everything.
*Cause:* the initial design fights the requirement.
*Catch:* when the third unrelated file appears in the diff, stop. Restore the
baseline and either shrink the task or raise the design problem explicitly.

### 16.7 The ignored warning

*Symptom:* the bug was announced by a deprecation notice, a log line, or a
comment six months ago.
*Cause:* warnings are treated as noise.
*Catch:* when you touch a file, read its warnings. When you add a warning,
make it actionable or remove it.

---

## 17. Checklists and templates

### 17.1 Universal task checklist

- [ ] Request restated in one sentence; ambiguities resolved
- [ ] Codebase explored: relevant code, tests, callers, configuration
- [ ] Plan written: goal, steps, files, verification, risks
- [ ] Change is the smallest that solves the problem
- [ ] Failure paths decided and handled
- [ ] Tests written and run; the bug test watched failing first
- [ ] Full suite run on the final revision
- [ ] The actual user path exercised end to end
- [ ] Diff self-reviewed as a stranger
- [ ] Commit messages describe one logical change each
- [ ] Report separates verified from unverified
- [ ] Nothing unrelated was touched

### 17.2 Bug-fix checklist

- [ ] Reproduced consistently
- [ ] Error read in full; recent changes checked
- [ ] Root cause identified — not guessed
- [ ] Failing test written and watched failing
- [ ] Minimal fix applied; unrelated cleanup deferred
- [ ] Test now passes; suite stays green
- [ ] Original symptom re-checked against the fix
- [ ] A regression test guards the specific failure

### 17.3 Code-review checklist

- [ ] The change does what the description says
- [ ] No unrelated changes
- [ ] Naming is honest and consistent
- [ ] Error handling is explicit and observable
- [ ] Edge cases are covered by tests
- [ ] No secrets, credentials, or debug leftovers
- [ ] Interfaces changed are documented and consumed correctly
- [ ] Performance characteristics are acceptable for the expected load

### 17.4 Incident checklist

- [ ] Capture state before changing anything: logs, metrics, error output
- [ ] Identify the last known good version
- [ ] Bound the blast radius; communicate status
- [ ] Apply the smallest safe mitigation
- [ ] Verify the original symptom is resolved
- [ ] Write the timeline while it is fresh
- [ ] Add a permanent regression test
- [ ] Fix the cause, not just the symptom, in a follow-up

### 17.5 Commit message template

```
<area>: <what changed, imperative mood>

Why: <the problem this solves, one or two sentences>

How verified: <command run and result>
Not done: <known gaps, if any>
```

### 17.6 Status report template

```
Status: <one line>
Done: <bullet list, each with evidence>
Next: <the next concrete step>
Blocked: <on what, since when, what you need>
```

---

## 18. Worked examples

### 18.1 A bug fix done right

*Task:* "Users report the export button sometimes produces an empty file."

1. **Understand.** The word "sometimes" is a lead. Ask: which users, which
   data, which browser? The reporter says it happens on large accounts.
2. **Explore.** Read the export handler, the query, and the tests. The query
   paginates; the handler writes each page. The tests use a three-row fixture.
3. **Reproduce.** Create an account with 1,200 rows; the export truncates at
   exactly 1,000. Now the failure is deterministic.
4. **Hypothesize.** "The pagination loop stops after the first page because
   the cursor is not advanced when the page is exactly full."
5. **Test first.** Write a test with 1,001 rows; watch it fail with a
   truncated file. The failure message matches the hypothesis.
6. **Fix.** Advance the cursor unconditionally; guard against infinite loops
   with a maximum iteration count and a logged warning.
7. **Verify.** The new test passes; the old tests pass; a 50,000-row export
   produces the correct checksum; the empty-account export still works.
8. **Report.** "Fixed: cursor was not advanced on exactly-full pages.
   Verified with 1,001 and 50,000-row accounts; checksum matched. Not
   verified: the mobile client's download flow."

### 18.2 A feature done right

*Task:* "Add a `sort` parameter to the list endpoint."

1. **Clarify.** Which fields are sortable? What is the default? What happens
   on an invalid field — 400 or ignore? The answers: name and created_at;
   default created_at descending; invalid field returns 400 with the allowed
   list.
2. **Interface first.** Write the documented contract: `?sort=name|-created_at`
   (leading minus for descending). Add examples.
3. **Implement.** Parse and validate the parameter; map to the existing query
   builder; reject anything else with the documented error.
4. **Test.** Valid ascending, valid descending, invalid field, missing
   parameter, and a field that exists but is not sortable.
5. **Verify end to end.** Call the running service with each case; confirm
   the JSON ordering, not just the status codes.
6. **Report.** Contract documented; five cases verified with transcripts;
   performance on 100k rows checked; index added for the name sort.

### 18.3 A refactor done right

*Task:* "The billing module is hard to test; clean it up."

1. **Understand the pain.** The tests need a live database and a network
   fake; they take four minutes and flake weekly.
2. **Plan the seams.** Introduce a repository interface for the data access;
   inject the payment client; keep behavior identical.
3. **Characterization tests first.** With the current code, capture the
   behavior of the main flows — including the ugly edge cases — so the
   refactor has a safety net.
4. **Refactor in steps.** Each step is a commit; each commit keeps the suite
   green. No behavior changes mixed into structural changes.
5. **Verify.** The characterization tests pass unchanged; the new unit tests
   run in milliseconds; the old integration tests still pass.
6. **Report.** "Behavior preserved (characterization suite unchanged); test
   time 4m → 3s; no production behavior changed."

### 18.4 A debugging session done right

*Task:* "Intermittent 502s from the checkout service."

1. **Reproduce/bound.** The 502s correlate with deploys. Not intermittent —
   correlated.
2. **Evidence.** Load balancer logs show upstream connection resets during a
   window of about ninety seconds after each deploy.
3. **Hypothesis.** "The new instances accept traffic before the database
   pool is warm; the first queries exceed the client timeout."
4. **Test.** Add a readiness check that exercises the pool; deploy to
   staging; the window disappears.
5. **Fix.** Gate readiness on a real query; add a metric for pool warm-up
   time.
6. **Guard.** Add a deploy-time smoke test that fails if the first request
   exceeds the threshold.
7. **Report.** Root cause, fix, guard, and the metric that will show the
   problem returning.

---

## Final word

The rules in this playbook are not original and they are not clever. They are
the accumulated hygiene of people who have been paged at three in the morning
by code that looked fine. The value is not in knowing them — every experienced
engineer knows them. The value is in doing them when the task is boring, when
the deadline is close, when the change "obviously" cannot break anything. That
is exactly when the expensive mistakes are made.

Plan before you type. Test before you claim. Debug from evidence. Review your
own diff. Report honestly. Everything else is detail.
