# Full-profile lower bound

The model remains uniform 20-of-80 draws, twenty distinct cards of sizes 2–10,
arbitrary overlaps, and frozen Spot Keno Pay Table 4. Record A remains an
achievable record; global optimality is open.

For each connected shared-number component, the existing full-profile engine
enumerates every card-size allocation and every shared-number hit state. A
repeated edge is retained as a distinct physical shared number; its independent
hit bit is included. Private-number selections receive exact binomial weights.
At each total incidence count, coefficientwise minima over the component's
profiles give a lower envelope. Nonnegative convolution and coefficientwise
minimization over compatible component totals preserve lower bounds. The residual
disjoint-card envelope enforces exactly twenty cards and exactly 86 incidences;
the final coefficient counts 20-number draws on full support 80. Relaxations
that admit duplicate cards only enlarge the allocation domain, so cannot raise
the lower bound or omit a legal distinct-card layout.

The ordinary path uses integer coefficient convolution. The packed path rebuilds
full profiles using 81-bit lanes. Subset-count coefficients for at most 80 physical
numbers are bounded by 2^80, preventing carries between lanes. Both the initial
computation and a fresh-process replay must agree on the lower bound and the
number of feasible combined incidence totals. An incomplete computation or replay
keeps its key open. No conditional/grouped envelope is used in this run.

The priority key is [[0,1],[0,1],[0,2],[1,3],[2,3],[4,5]]. Its two identical
[0,1] edges are two distinct shared numbers. Both independent executions give
8237478838272 across 45 feasible totals, exceeding Record A's 1099511627776.
This certifies an exclusion for the geometry, not an attainable layout or a
new witness. No improving witness was produced.
