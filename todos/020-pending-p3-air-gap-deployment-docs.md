---
status: pending
priority: p3
issue_id: "020"
tags: [deployment, air-gap, enterprise]
dependencies: ["011"]
---

# Document Air-Gap Deployment Path

## Problem Statement

Some enterprise environments require air-gapped deployment compatible with restricted dependency environments. Brand Arbiter's provider abstraction (TODO-011) naturally supports this, but the deployment path needs documentation.

## Acceptance Criteria

- [ ] Deployment guide for air-gapped environments
- [ ] List of all dependencies with offline installation notes
- [ ] Instructions for configuring VLM provider to use internally-hosted models
- [ ] Docker or similar packaging option for self-contained deployment

## Notes

- Deferred per project owner's decision: "Proof of value first, unconstrained. Air-gap is optimization."
- The VLM provider abstraction (TODO-011) already supports swapping API providers — air-gap deployment is a configuration change, not an architecture change
- Document when an enterprise customer requires it, not before
