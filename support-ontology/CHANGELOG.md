# Changelog

All notable changes to the generic Support Organization Ontology bundled with
ticketmask. Newest entries at the top. Dates are `YYYY-MM-DD`.

Change types: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Decided`.

---

## 2026-10-16 — Generic release

### Changed
- Organization-specific individuals replaced with templates: the product
  working set (`Entities/Product.md`) and the CRM instance table
  (`Entities/CRM.md`).
- Severity definitions (`Entities/SeverityLevel.md`) rewritten as generic
  templates. Adopting organizations should substitute their own support policy.

### Added
- `scripts/` — `validate_ontology.py`, `export_glossary_csv.py` and the
  `build_graph.py` parser they share.
- `Export/support-ontology-glossary.csv` — generated; ticketmask checks its
  entity bindings against it.
