## Pre-existing test failures discovered during 75-02 execution

- tests/test_dashboard_scan_history.py::test_compare_self — test asserts old detail format ("Cannot compare a scan to itself.") but route now returns canonical format_error("DASHBOARD-007") string. Pre-existing on HEAD prior to 75-02 work. Not in 75-02 scope.
- tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score — test expects 200 from /score with no answered questions, but route correctly returns 422 (DASHBOARD-011 "no answered questions"). Pre-existing on HEAD prior to 75-02 work. Not in 75-02 scope.
- tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success — KeyError, unrelated to API/CLI scope. Pre-existing.
