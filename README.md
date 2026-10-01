# Ticket Analyzer Agent

A small LangGraph agent that triages incoming support tickets — assigns a priority, then
either resolves the ticket itself, assigns it to a team, or closes it as unsupported — kicked
off by ticket events arriving on a Pub/Sub topic.

Heads up: this is a demo, not something we run in production. It's here to show a particular
way of building an event-driven agent — the full ticket record riding in the event instead of
a lookup tool, and a real (if minimal) GCP deployment built entirely on managed/serverless
pieces (no VM or container you have to keep running). See the bottom of this doc for what's
deliberately left out.

## Architecture

![Architecture Diagram](docs/architecture.svg)

A ticket is published directly onto the `support-tickets` Pub/Sub topic, which fires an
Eventarc trigger that pushes the message to `agent/cloud_function.py`, deployed as a Cloud Run
function, which hands off to `agent/processor.py` → `agent/graph.py`.

There's no standalone consumer process anywhere in this project — the Cloud Run function is
the only thing that runs the agent.

## The whole ticket rides in the event

There's no `get_ticket_data` tool, and no ticket database the agent queries. The Pub/Sub
message *is* the ticket — subject, description, customer, product, category, all of it — and
`agent/processor.py` drops that JSON straight into the prompt. The agent never looks anything
up; it just reasons over what it was handed.

The three terminal tools don't persist anywhere either — they just log the outcome
(priority, status, resolution/team/reason) and return a confirmation string. For a real
system that'd write to whatever ticketing backend issued the event; for this demo, structured
logs (visible in Cloud Logging for the Cloud Run path) are the outcome record.

## Exactly one terminal action, every time

The system prompt in `agent/graph.py` is deliberately narrow: assign a priority
(Critical/High/Medium/Low based on customer impact and urgency), then call exactly one of
three tools —

- `auto_resolve_ticket` — well-understood, self-service issue the agent can fully answer
  itself (how-tos, documented workarounds, account/password guidance).
- `assign_ticket` — needs a human with system access or judgement (bugs, billing disputes,
  security incidents), routed to one of five fixed teams.
- `close_as_not_supported` — out of scope, unsupported, or spam.

No open-ended tool loop, no "keep going until you feel done." One ticket in, one decision
out, every time.

## Claude via Vertex AI, not a direct API key

The model call goes through `langchain_google_vertexai.ChatAnthropicVertex`, hitting the
Claude Sonnet 5.5 deployment enabled in Vertex AI Model Garden. There's no
`ANTHROPIC_API_KEY` anywhere — auth is Application Default Credentials
(`gcloud auth application-default login` locally, the function's own service account on
GCP), same pattern as the rest of the project's GCP access.

## Running locally

There's no standalone consumer in this project — `scripts/produce_test_ticket.py` publishes
to the real Pub/Sub topic, and the deployed Cloud Run function is what actually processes
tickets.

```bash
uv sync
cp .env.example .env   # fill in GCP_PROJECT_ID
gcloud auth application-default login   # needed for both Vertex AI and Pub/Sub publish auth
uv run python scripts/produce_test_ticket.py   # publishes every ticket in scripts/tickets.json
```

## Running on GCP

Terraform (`terraform/`) provisions all of it:

- `google_pubsub_topic.support_tickets` — the `support-tickets` topic producers publish to and
  Eventarc triggers off (`terraform/pubsub.tf`).
- `google_cloudfunctions2_function` (branded "Cloud Run functions", same API either way) with
  an Eventarc trigger on that Pub/Sub topic, plus two purpose-scoped service accounts:
  `ticket-analyzer-fn` (`roles/aiplatform.user`, so the function can call Vertex) and
  `ticket-analyzer-trigger` (`roles/eventarc.eventReceiver` + `run.invoker`, so Eventarc can
  invoke it). Pub/Sub's own service agent is granted `roles/iam.serviceAccountTokenCreator` on
  the trigger's service account so it can mint the OIDC tokens that invoke Cloud Run.
- A GCS bucket holding a placeholder deploy — Terraform only creates the function, it doesn't
  own the code.

Whoever runs `scripts/produce_test_ticket.py` needs `roles/pubsub.publisher` on the topic or
project — not granted by this Terraform, since that's a human/local ADC identity rather than a
service account this project owns.

GitHub Actions (`.github/workflows/deploy-agent.yml`) does the actual code deploys: it's
path-filtered to `agent/**`, and runs `gcloud functions deploy` without touching trigger or
IAM config, so it can't accidentally drift what Terraform manages.

## What's missing, on purpose

- The three terminal tools don't persist their outcome anywhere — no database, no file. Fine
  for a demo where Cloud Logging is the record; a real system would write back to whatever
  ticketing backend issued the event.
- Claude on Vertex AI Model Garden ships with a default request quota of effectively zero for
  new projects — `global_online_prediction_requests_per_base_model` has no allocated limit
  until you request one in the Console (IAM & Admin → Quotas). Nothing in this repo can fix
  that; it's a one-time manual step per project.
- No automated tests — correctness so far has been checked by hand: the producer publishes to
  the real topic, and the Pub/Sub → Eventarc → Cloud Run push path is confirmed to actually
  fire (instances scale up on message arrival). Full agent processing end-to-end is still
  blocked on the Vertex AI quota above.

All fixable, just not the point of this project.

---

**Need this reliable in production, not just as a demo?** [Arul Systems](https://www.arulsystems.com/)
helps customers build reliable agents quickly, at scale. [Get in touch](https://www.arulsystems.com/contact).
