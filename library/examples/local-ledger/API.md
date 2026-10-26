# Local ledger example

Original synthetic fixture and React hook. Import `usePocket` from `usePocket.js`; keep `data.js` beside it. Host needs React and a browser. This is a reusable state slice, not a bank connector or production accounting engine.

Hook returns rows, warning, busy, error, notice, save(record,{simulateFailure}), clearError, clearWarning. `save` resolves boolean, validates first, locks simultaneous writes, commits localStorage before visible state, preserves committed rows on failure. Caller owns editor draft/UI. Persistence keys are exported; namespace them before combining products. Application owns privacy/deletion policy. No backend, synchronization, authorization or multi-tab conflict guarantee.

Data exports accounts/opening balances, categories/monthly budgets, synthetic transactions, totals, accountBalance, parseAmount, validDate, validateRecord, money. Amounts are positive integer kopecks. Transfer debits source and credits destination; income/expense/budget totals exclude transfers. The public starter has zero opening balances at OPENING_DATE (2025-01-01), an empty transaction seed, and an illustrative snapshot ending 2025-01-31. Fixture dates are bounded to the demonstration snapshot; replace those constants with the actual product contract on reuse.

This hook is a source example, not a rendered or visually approved application. The consuming application must verify save/retry, editing and reload behavior. Source hashes pin the distributed files.
