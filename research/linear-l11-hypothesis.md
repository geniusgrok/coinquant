# L11 preregistration: reversal exit with original stop ratchet

L9 changed two holding mechanisms together and failed liquidation criteria.
L10 long-only restriction then worsened CAGR to4.22% and MDD to17.36%; rejected.
Negative standalone short gross profit did not imply that dropping shorts would
improve the continuous portfolio; do not repeat that direction or tune thresholds.

L11 isolates the reversal-exit component against exact L7: keep original ten-day
stop tightening and both directions, but close an existing position when the
completed-daily persistent regime reverses at a frozen invocation. No same-trigger
reversal. Entry risk .006, cap2x,20x exchange and all other rules unchanged.
Exactly one run; retain only for CAGR and CAGR/MDD above L7, MDD<50%, and no more
than2 liquidation classifications. Development only. If failed, stop this holding
family and inspect participation sizing and native execution ambiguity before
registering a different entry structure. No2024+economics or parameter sweep.
