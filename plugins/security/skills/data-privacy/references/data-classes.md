# Data classes

Read this when classifying a field in step 2 and you need the taxonomy, or when a class
boundary is disputed. The classes are ordered by what mishandling them costs.

## The classes

**Direct identifiers.** Name, email address, phone number, account number, government
identifier, device identifier, precise location. A single value usually names one person. These
are what a subject request retrieves by, and what a breach report counts.

**Indirect identifiers.** Postcode, date of birth, job title, employer, browser
fingerprint. None names a person alone; small combinations do. The standard result here is
that postcode, date of birth and sex together identify most people in a population, which
is why treating these as harmless individually is the mistake the class exists to prevent.

**Special-category data.** Health, biometrics, genetics, race or ethnicity, religion,
political opinion, trade union membership, sex life or sexual orientation. Most regimes
give these a separate and stricter regime with a narrower set of lawful bases. Treat any
field in this class as requiring its own justification, not the system's general one.

Criminal offence data usually sits beside this class under its own rule. Check what binds
you rather than assuming it is included.

**Inferred attributes.** Anything derived rather than collected: a risk score, a predicted
preference, a segment. These inherit the sensitivity of what they imply, not of what they
were computed from. A purchase-history segment that separates pregnant customers is
special-category data however ordinary its inputs were.

**Pseudonymised data.** Real personal data with identifiers replaced by a key you still
hold. It is still personal data, and it belongs in the inventory. The reduction in risk is
real and the change in classification is not.

**Anonymous data.** Personal data only where re-identification is not reasonably possible
by anyone, including you, including by joining what you hold to what is public. If you
kept the key, the salt or the mapping table, it is pseudonymised. This class is much
smaller than people assume, and claiming it wrongly is how a dataset gets shared under an
exemption that does not apply.

## What each class implies

| Class | Retention | Access | Deletion |
| --- | --- | --- | --- |
| Direct identifier | Shortest period that serves the stated purpose | Logged, and reviewed | Every surface, plus the suppression list |
| Indirect identifier | As above; the combination is what matters | Logged where combinable | Every surface |
| Special category | Justified separately, usually shorter | Explicit grant, never a default role | Every surface, and prove it |
| Inferred attribute | Tied to the inference's usefulness, not the input's | As its implied class | Recompute or delete; a stale score outlives its input |
| Pseudonymised | As the underlying class | As the underlying class | Delete the key as well as the rows |
| Anonymous | Out of scope, if the claim holds | Out of scope here | Not applicable |

## Classifying a field in practice

Three questions, in order. What is the worst thing this field can contain, not what it
usually contains. Who would be harmed if this field alone leaked. What does this field let
someone do when joined to something public.

A field whose answers are "anything", "the user" and "find their address" is a direct
identifier however it is labelled in the schema.
