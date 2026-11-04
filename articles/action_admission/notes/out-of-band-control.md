# Out-of-band control of agent actions on top of evidence

Concept note, 2026-11-04. Working material for the third article in the series
(after thread admission and tool admission). Not article text.

## 1. The problem

An assistant acting for a person reads the person's request, tool results, files,
web pages and messages written by other people. All of that becomes one model
context. The model then proposes actions, and some of them have consequences:
send, delete, pay, share.

Inside that context there is no boundary between the person's instructions and
other parties' text. A message from a contact saying "forward this to everyone"
sits next to the owner's request with the same standing. This is in-band
signalling: control and data share one channel.

Telephony had the same flaw. Trunk control tones travelled in the voice band, so a
2600 Hz tone played into the handset could seize a long-distance line. The fix
was not a better tone detector; control moved out of band (SS7). The browser
reached the same conclusion with the same-origin policy: content carries an origin
label that it cannot forge, and a component outside the content checks that label
whenever the content tries to act.

Voice assistants met the problem directly. Speech from a television (a news anchor,
an advertisement) reached a speaker as if its owner had spoken. Vendors could not
reliably tell who was speaking, so they limited consequences instead: suppression
of known broadcast audio, voice codes and phone confirmation for purchases.

## 2. Position: intent belongs to the principal

The model is not a subject and has no intent. Intent exists only in the principal's
turn: the request they made, within limits they set. The model produces proposals:
interpretations of that intent.

A proposal becomes the principal's action in one of two ways:

- **Within a pre-declared envelope.** The principal has already said what may happen
  without them (read, yes; send, no). Precedents: approval and sandbox policies in
  coding agents, intent mandates in agent payments, device replenishment limited to
  products the owner selected.
- **By ratification.** The principal sees the concrete action with its exact
  arguments on a surface the model cannot write to, and approves it. Precedents:
  dynamic linking in payment authentication (the code is bound to amount and payee),
  browser-rendered payment confirmation, agency-law ratification.

The service never needs to decide whether the model understood the intent. It needs
to ensure that no consequence occurs outside the principal's envelope without their
ratification.

Identity of the acting software is not the missing piece. Delegation standards
already separate the principal from the actor. What is missing is a reliable answer
to "which parties' text could have produced this proposal", available to a component
outside the model.

## 3. What the first two articles provide

- **Model-call evidence** (thread admission): for one completed call, the ordered
  input and output, with roles, types and content, signed by the inference proxy and
  checkable after the history has passed through client custody.
- **Tool-executor evidence** (tool admission): what the executor received and
  returned, with a `source_class` describing how it obtained the result.

Together they are origin labels for every element of a model context that survive
transport. That is the precondition the same-origin policy relies on.

| Same-origin policy needs | Evidence gives |
|---|---|
| An origin label on each piece of content | Yes: per element of call input and output; per tool result with its source class |
| The label survives transport and cannot be forged by content | Yes: signed statements checked by the receiver |
| An enforcement point outside the content | Becomes possible: the tool executor or a policy point checks labels before a consequential call |
| Which input caused an action | No: a signed call proves "given inputs A, B, C the model output call X", not that B caused X |

## 4. The mechanism: information-flow control with evidence as labels

1. **A call's label is the least trusted label of its inputs.** If any input element
   is third-party text, or lacks evidence, everything the model output in that call
   carries the third-party label. Conservative, but sound without knowing causation.
2. **Labels propagate.** An assistant message produced from labelled input keeps the
   label when it is sent again. A summary of labelled content is labelled. An element
   without evidence is untrusted (fail closed).
3. **Enforcement at the tool boundary.** A consequential tool runs without the
   principal only when the model call that requested it carries no label beyond
   "principal" and "trusted system". The check uses signed metadata, not text in the
   context: control is out of band.
4. **Ratification is the only declassification.** Otherwise the action goes to the
   principal on a trusted surface, bound to its exact arguments. The decision record
   references the call evidence it ratifies.

## 5. Missing building blocks

1. **Principal-voice evidence at ingress.** Thread admission notes that a `user` role
   in a call's input is client-supplied context. A separate statement is needed when
   the turn starts: this message was submitted by principal P through their
   authenticated session, in turn T. Without it the principal's request cannot be told
   apart from text a client inserted.
2. **Source classes that separate other people's text.** Knowing that a result came
   from a given executor is not enough. The class must distinguish system data (a
   list of conversations), the principal's own data, and third-party content (the
   body of a contact's message, a fetched page). This extends `source_class` from tool
   admission with a trust-relevant dimension.
3. **Binding a tool invocation to the model output that requested it.** The
   enforcement point must know which signed call produced the invocation it received.
   Options: match the invocation's tool name and argument hash against signed outputs
   of the same principal; or carry a reference to the call in the invocation. The
   first needs no protocol change; the second is cleaner but extends the tool protocol.
4. **A chain across calls.** Single-call evidence does not prove that an assistant
   message in the input is a genuine earlier model output. Propagating labels needs
   the evidence of the call that produced each such message; without it the message is
   untrusted.

## 6. Limits

- **Coarseness.** Most useful turns read third-party text; reading a person's messages
  is often the task. Nearly every consequential action after such reading needs
  ratification. That matches how voice assistants and payments behave, but
  ratification must be cheap and precise.
- **Text the principal pasted** carries the principal's label. It is their
  responsibility, as with the owner's own voice at a speaker.
- **Calls outside the evidence path** (a local model, a tool without evidence) stay
  untrusted.
- **Fine-grained causation** ("the recipient argument came from that message")
  requires an architecture that separates planning from processing untrusted data, as
  in dual-model designs. Evidence makes such a design checkable across custody; it does
  not replace it.

## 7. Prior art to position against

- Information-flow control and taint tracking (Denning's lattice model, 1976).
- Same-origin policy; in-band versus out-of-band signalling (2600 Hz, SS7).
- Dual-LLM pattern (Willison, 2023); CaMeL (Google DeepMind, 2025): capabilities and
  data-flow tracking for prompt-injection defence.
- Payment authentication: PSD2 dynamic linking; Secure Payment Confirmation.
- Agent payments mandates (intent and cart); device replenishment with
  owner-selected products.
- Delegation semantics in token exchange (principal as subject, actor separate).
- Legal attribution of electronic agents' actions to the person using them (UETA;
  UN Convention on Electronic Communications).

## 8. Claimed contribution

Composing model-call evidence and tool-executor evidence as information-flow labels,
enforced outside the model at the tool boundary, with principal ratification on a
trusted surface as the only declassification, so that the rule stays verifiable when
the history is held by the user and returns from other runtimes.

Open for the article: whether to specify the binding of an invocation to its call
(§5.3) as a proposed profile, and whether to include a runnable example built on the
fixtures and evidence formats of the first two articles.
