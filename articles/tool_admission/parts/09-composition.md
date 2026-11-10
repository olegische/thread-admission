## Conclusion

A returned thread can contain tool results from executors the receiving service did not operate. Model evidence establishes what the model was shown, and the service also needs evidence of where a tool result came from.

- The executor signs a statement about the call, its arguments, its result and how it obtained that result, with a reference to the model-call evidence.
- The receiving service verifies both statements, checks the reference and compares the values they cover.
- Each tool record receives one of four statuses: Restored, Produced, Shown or Supplied.
- Restored links the executor's result to what the model was shown. The service's policy uses the source class to decide whether that result can support an action.

Two questions remain for future work: how to admit separate records of a decision before an operation and its outcome, as described in the work following SEP-2828, and how to verify chains of evidence passed between agents.

The discussions in the MCP community, cited in section 1, informed this work.

### Run the examples

The example implementation, fixtures, schemas and the check script that keeps the code and this text in agreement are in the [companion repository](../../../README.md) alongside the earlier article's examples. The [executed-checks note](../notes/executed-checks.md) records the results and limits. The profile has been checked on fixtures and remains a proposal for use with a real runtime.
