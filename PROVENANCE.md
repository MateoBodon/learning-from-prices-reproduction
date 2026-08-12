# Provenance

The independent code in this repository examines the model and source record
associated with:

- Francesca Bastianello and Paul Fontanier, “Expectations and Learning from
  Prices,” *The Review of Economic Studies* 92(3), 1341–1374 (2025),
  https://doi.org/10.1093/restud/rdae059.
- Francesca Bastianello and Paul Fontanier, “Replication Package for:
  Expectations and Learning from Prices,” Zenodo, version v1 (2024),
  https://doi.org/10.5281/zenodo.10780393.
- Francesca Bastianello and Paul Fontanier, “Online Appendix for: Expectations
  and Learning from Prices” (2024), especially Sections D, F, and G,
  https://paulfontanier.github.io/papers/onlineappendix_PETinGE_BF_Restud.pdf.

The SHA-256 digest recorded for the cited Zenodo v1 archive is
`812151e7045c7b16478a6023d48dc1bbe2f7802d0d5d0c9ca010991af9d367c6`.
That archive and its extracted files are not included here. The Zenodo record
does not display a license value, so this repository makes no redistribution
claim about its contents.

`provenance/recorded_source_checks.json` reports narrow comparisons retained
from one unmodified MATLAB R2023b Update 11 execution. That execution returned
normally and created 11 MATLAB figure objects. Agreement is reported only for
MATLAB objects 10 and 11, corresponding to the deposited online-appendix
Figure 6 and Figure 8 routines, and for the deposited-denominator coefficient
vector. MATLAB objects 1–9 were not independently reconstructed. Seven bounded
solver calls printed non-success diagnostics. The retained execution is not
repeated by this repository, and no displayed figure or economic conclusion is
claimed to change because the discrepant fixed-point output is assigned but
not subsequently read by the plotting driver.
