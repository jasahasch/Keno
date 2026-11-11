# Attachment-preserving grouped conditional envelopes

The accepted priority implementation is `tools/incidence86_grouped_strict.py`.
The earlier numerical-interface grouping is retained as diagnostic source and evidence;
its provisional certificates do not determine final priority dispositions.

A shared number is a node joining its incident cards. In each tree, root at a
maximum-degree card (the shared hub in these cases). For a single cycle, remove
one card–number incidence that leaves a connected tree and condition on that
number's hit bit. The removed incidence still contributes to its original
card's shared degree, private-number count, and hit constraint.

Each child message records every feasible total card size and both boundary-hit
polynomials. Two branches are grouped only when their complete rooted attachment
signatures, cycle-cut restrictions, and conditional polynomial tables coincide.
The signature retains original shared degrees and all descendants, marks the cut
card and cut number, and uses the same frozen size-dependent payout caps. Thus it
preserves all attachment and payout constraints; equal numerical floors alone
are insufficient for this reduction.

For a group of r exchangeable branches, enumerate combinations with replacement
of their feasible total/message entries. Every labeled allocation has a sorted
representative; permutations preserve the hub's size sum and conditional product.
No allocation multiplicity factor belongs in a minimum over allocations. For each
representative, a separate DP multiplies the conditional polynomials for each
branch and sums over all physical hit-bit assignments, retaining their total hit
count. This DP DOES count distinguishable selected branches: equal factors still
appear r times. Its products are reused for each permitted hub size and inherited
boundary hit. All private hit counts have exact binomial weights. A shared number
contributes one power of x at its parent card, never once per incident card.
The two cut-bit states are added only after the corresponding conditional floors.

At fixed total incidence count, coefficientwise minima give lower envelopes.
Nonnegative convolution, addition over hit states, and subsequent coefficient
extraction preserve lower bounds. Conditional minimization can yield a strict
lower bound rather than an attainable polynomial; this is expected, including
on the hyperedge and cycle fixtures. Every legal allocation remains covered.
No improving witness or global optimum is claimed.

Exactly 86 incidences and full support 80 leave six excess memberships. The
unchanged residual-card envelope enforces twenty total cards and sizes 2–10.
Distinctness in all seven priority geometries is automatic: all shared-membership
sets of degree at least two differ, while degree-one cards necessarily have a
unique private number. Residual cards and separate components are disjoint.
The general inherited envelopes remain lower bounds even if their relaxation
also admits an illegal duplicate; they never omit legal distinct-card layouts.

Ordinary arithmetic uses integer coefficient convolution. Replay uses base
2^81 packed multiplication, separately rebuilding the envelopes and residual
polynomials. Every intermediate counts subsets of at most 80 physical numbers,
so its coefficients are bounded by 2^80 and cannot carry between 81-bit lanes.
Final acceptance requires equal lower bounds AND feasible combined-total counts,
and a floor at least 1099511627776. Incomplete ordinary or packed work stays open.

The direct oracle enumerates all card sizes 2–10 and all shared-number selection
states on six small fixtures: an edge, two- and three-leaf stars, a triangle,
a triangle with a pendant edge, and a tree with a three-card shared number.
It checks equal feasible-total sets, ordinary/packed equality, and that every
lower-envelope coefficient is at most its direct counterpart. Simple pair-edge
stars also require exact coefficient equality. The oracle is the unchanged
full-profile evaluator, not the conditional message implementation.
