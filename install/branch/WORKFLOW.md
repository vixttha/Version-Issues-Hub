# VIB workflow

Head → Worker → Validate → Internal Auditor → Head. One active Worker. Head approves scope, the Worker changes the product on a separate work branch, Validate records test evidence for the exact candidate, Internal Auditor checks scope and evidence, Head returns the decision to the repository owner. The owner controls merges and releases.

Keep the VIB ledger and policy on this dedicated branch. Read the adopter identity and baseline in vib-install.json and the authoritative GitHub issue before assigning work. Do not overwrite existing assignments or product instructions. VIB is standalone; it is not Provenistem. Required GitHub merge enforcement is optional and disabled at installation. This guide is not proof of enforcement or cross-harness evaluation.
