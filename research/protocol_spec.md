# Commitment protocol requirements (design only)

No distributed commitment protocol has been implemented or proven in this
milestone. The simulator has no resource-grant service and no hidden safety lock.

Required before M5: define request IDs and resource owners; REQUEST -> GRANT ->
COMMIT -> RELEASE -> ACK transitions; duplicate handling; generations for old
requests; deterministic simultaneous-request priority; retry budgets; and
recovery after participant interruption. A late grant cannot silently authorize
a newer request. An absent release/ACK must fail closed or use an explicitly
trusted local clearance observation. Expiry alone never demonstrates clearance.

Tests must separately lose each transition message, reorder prior generations,
stop an owner while extended, and hold a goal at a doorway. Record safety and
noncompletion separately. Add starvation/age behavior only after a minimal
correct resource protocol and meaningful matched baselines exist.
