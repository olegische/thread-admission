# Action admission — working directory of the third article

The idea was recorded on 2026-11-04. There is no article text yet; this directory
holds the concept and the material the article will be written from.

- [Concept](notes/out-of-band-control.md) — problem, mechanism, missing building
  blocks, limits, prior art

## The idea in one sentence

The first two articles provide verifiable origin labels for everything that enters a
model context: evidence of model calls (thread admission) and evidence from the tool
executor (tool admission). The third article builds out-of-band control on top of
them, as SS7 did in telephony: the model remains the "band", and the decision about a
consequential action is made by an enforcement point outside the model, from signed
source labels, with the principal's ratification as the only way to remove a label.

## Place in the series

1. **Thread admission** — which parts of a returned history can be restored.
2. **Tool admission** — what a service may consider established about a tool record
   it did not witness.
3. **Action admission** — which actions may run without the principal when the
   context they were proposed from contains other parties' text.

## Editorial norms

As in the first two: a concrete situation, the receiving side's problem, then its
solution. Roles are generic (principal, runtime, inference proxy, tool executor,
enforcement point, trusted confirmation surface), without the specific systems and
services in which the topic arose.

## To verify before writing (CHECK)

1. The 2017 smart-speaker incidents (a news broadcast and a dollhouse order; the
   Burger King advertisement and "OK Google") and vendors' countermeasures
   (acoustic fingerprints of their own broadcasts, voice codes for purchases) —
   against primary sources.
2. CaMeL (Google DeepMind, 2025, "Defeating Prompt Injections by Design") and the
   dual-LLM pattern (Simon Willison, 2023) — exact titles, dates and what they claim.
3. Denning 1976 (the lattice model of information flow) — reference.
4. PSD2 dynamic linking: Article 97(2) PSD2 and Article 5 of the RTS — wording.
5. UETA (1999) "electronic agent" and the UN Convention on the Use of Electronic
   Communications (2005), Article 12 — wording on attributing a program's actions to
   a person.
6. In-band signalling: 2600 Hz and the move to SS7 (out-of-band) — dates and an
   accurate technical description.
7. Same-origin policy — reference to the specification (HTML / Fetch).
