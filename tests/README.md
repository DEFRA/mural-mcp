# Tests

Full rules: [docs/python-testing-standard.md](../docs/python-testing-standard.md). This is the
short version to place a new test correctly without opening that file.

## The placement rule

> A test goes in `tests/integration/` if and only if it enters through an ASGI request into a
> FastAPI app, or an MCP call through a `fastmcp.Client`. Otherwise it goes in `tests/unit/`,
> mirroring `app/`.

Don't ask "how integrated is this?" -- that question has no stable answer. Ask only whether the
test crosses one of the application's own front doors. A test that builds its own `FastAPI()`
and issues a request is an integration test even if it only mounts one router.

`tests/integration/` also happens to be the name of an unrelated production package
(`app/integration/`, the layer that talks to Mural) and, loosely, of the `@pytest.mark.vcr`
tests (which are integration tests too, just against a recorded vendor response rather than our
own app). That's accepted, not missed -- see
[docs/python-testing-standard.md §1.2.2](../docs/python-testing-standard.md#122-the-mirror-is-a-consequence)
for why. Placement is decided only by the rule above, never by the word.

| Directory | Holds | Named after |
| --- | --- | --- |
| `tests/unit/` | imports a module, calls it directly | the module, mirroring `app/` 1:1 |
| `tests/integration/` | an ASGI request or an MCP `Client` call | the capability, not the module |
| `tests/fakes/` | in-memory implementations of ports **we own** | the port |
| `tests/fixtures/` | the shape of data from systems we **don't** own | the external contract |
| `tests/support/` | app and container assembly (`tests/support/app.py`) | what it assembles |
| `tests/cassettes/` | recorded vendor HTTP responses (VCR) | the recording |

The same basename may legitimately appear in both `tests/unit/` and `tests/integration/` -- that's
the structure working, not a collision (`--import-mode=importlib` is what makes this collectable).

## Running

```bash
uv run pytest -q                  # everything except @pytest.mark.mongo
uv run pytest -q -m mongo         # the MongoDB round-trip tests (needs Docker)
uv run pytest -q -m vcr           # just the cassette-replay tests
uv run task test                  # lint + typecheck + full suite + coverage, what CI runs
```

`@pytest.mark.mongo` tests start a real MongoDB via testcontainers (session-scoped container,
a fresh database per test) -- Docker must be running.

## Recording cassettes

```bash
uv run task record                 # record cassettes that are missing
uv run task record -- --force      # re-record everything from scratch
uv run task record -- -k oauth     # limit to matching tests
```

Needs real Mural credentials in the environment; refuses to start without them. Backs up the
existing cassettes first, then runs the hygiene guard (`tests/unit/test_cassette_hygiene.py`)
over whatever was captured, and restores the backup and fails if anything secret-shaped got
through. Read `git diff tests/cassettes/` before committing -- that diff is the vendor's contract
changing, which is the most valuable thing a cassette ever tells you.

## When it doesn't fit

Ask the placement question first -- it always has an answer. If the capability has no file yet,
create one named after the capability; don't force it into a module-named file. If a test needs
a live external dependency, add a marker (`vcr`, `mongo`), never a new top-level directory.
