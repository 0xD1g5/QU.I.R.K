| UAT-7-08 | `src/dashboard/src/pages/__tests__/findings-filtering.test.tsx::"narrows the findings table to matching rows when a severity filter is applied"` | `findings.tsx`'s severity predicate was replaced with a constant-true one (`filtered.filter(() => true)`), so selecting CRITICAL left every row in place. | `AssertionError: expected [ 'crit-a.example.com', …(3) ] to deeply equal [ 'crit-a.example.com', …(1) ]` — received added `low-a.example.com` and `medium-a.example.com` (at `expect(afterFilter).toEqual([...CRITICAL_HOSTS].sort())`) | 69d05cc0 | 96592fca |
| UAT-7-09 | `src/dashboard/src/pages/__tests__/findings-detail-slideout.test.tsx::"opens the finding detail slide-out with the selected finding's fields when its row is clicked"` | The row `onClick` handler was changed from `openStoryline(row.original, row.id)` to `openStoryline(findings[0], row.id)`, so every row click opens the FIRST finding's drawer. | `TestingLibraryElementError: Unable to find an accessible element with the role "heading" and name "Bravo finding about an undersized RSA key"` — the DOM dump shows the drawer heading is `"Alpha finding about session resumption"` instead | 69d05cc0 | 96592fca |
| UAT-7-37 | `src/dashboard/src/pages/__tests__/findings-protocol-filter.test.tsx::"combines the protocol filter with the severity filter to narrow the findings table"` | The protocol branch was changed to re-start from the unfiltered list (`filtered = data.findings.filter((f) => f.protocol === protocolFilter)`), so each filter still worked alone but the two no longer intersected. | `AssertionError: expected [ 'tls-crit.example.com', …(1) ] to deeply equal [ 'tls-crit.example.com' ]` — received added `tls-low.example.com` (at `expect(currentHostSet()).toEqual([TLS_CRIT])`, the TLS+CRITICAL intersection assertion) | 69d05cc0 | 96592fca |

## Citations

UAT-7-08 -> `src/dashboard/src/pages/__tests__/findings-filtering.test.tsx::"narrows the findings table to matching rows when a severity filter is applied"`
- All three Pass Criteria bullets are covered: only CRITICAL rows shown (asserted as an exact row
  set plus an explicit absence check for each non-CRITICAL host), row count decreases, and clearing
  the filter restores all rows.
- **Divergence from the case's Steps, not its Pass Criteria.** Step 2 reads "Type `CRITICAL` in the
  filter", but the product implements severity filtering as a Radix `Select` dropdown
  (`findings.tsx:220-230`), not a text input; there is a separate free-text `Input` (`aria-label`
  "Search findings") that drives TanStack's `globalFilter`, which is a different control from the
  severity filter the case's Pass Criteria and the case's own GAP reason ("the severity filter
  input narrows visible rows") describe. The test drives the severity dropdown — the control that
  produces the described effect. No fixture or shim was invented to make the "type" wording true.

UAT-7-09 -> `src/dashboard/src/pages/__tests__/findings-detail-slideout.test.tsx::"opens the finding detail slide-out with the selected finding's fields when its row is clicked"`
- Partial coverage. One of the case's five Pass Criteria bullets is uncovered by this node:
  - "Panel closes when clicking outside or X button" — not asserted here; this node's subject is
    the open-with-the-right-finding flow, and folding a close interaction into it would give the
    node two subjects. The close path is already covered elsewhere in the tree, by
    `src/dashboard/src/pages/__tests__/findings-storyline.test.tsx`'s
    `"F5 + F6 (Escape): SheetContent unmounts and focus returns to the exact triggering button"`,
    `"F6 via the Close button: focus returns to the exact triggering button"`, and
    `"F6 via an overlay click: focus returns to the exact triggering button"` — each of which
    asserts the SheetContent unmounts. 206-13 may cite those as supplementary coverage of this
    bullet if it chooses; this plan does not flip any disposition.
  - The other four bullets are covered: the panel opens on click, the full description is visible,
    host/port/protocol/severity are all shown, and the quantum risk assessment is visible — all
    read from `FIXTURE.findings[1]`, with every one of `FIXTURE.findings[0]`'s distinctive values
    asserted absent.

UAT-7-37 -> `src/dashboard/src/pages/__tests__/findings-protocol-filter.test.tsx::"combines the protocol filter with the severity filter to narrow the findings table"`
- All seven Pass Criteria bullets are covered: the protocol dropdown is present alongside the
  severity one, the default reads "All Protocols" and shows every row, KERBEROS narrows to the
  Kerberos row, TLS narrows to the TLS rows, the option list is asserted to be exactly
  `All Protocols / TLS / SSH / HTTP / KERBEROS / SAML / DNSSEC`, the severity filter applied on top
  yields the intersection (and releasing only the protocol filter leaves the severity filter still
  in force), and "All Protocols" restores the full list.
- **Red-proof selection note.** The first mutation tried — making the protocol predicate constant-true
  — did make this node fail, but at line 106 (the protocol-ONLY assertion), which does not exercise
  the combination claim that is this case's distinctive subject. A second attempt (clobbering on the
  *severity* branch) passed green, because severity is applied first and protocol second, so a clobber
  there still yields the correct intersection — a reminder that a plausible-sounding mutation can
  fail to exercise the seam at all. The mutation recorded in the row above is the one that isolates
  the combination: it clobbers on the protocol branch, leaving each filter correct in isolation while
  breaking their intersection, and it fails at line 117, the intersection assertion itself.
