# Creative direction workflow

## Before drawing

1. Select an initial logo category based on the brief and first placement. Common categories include pictorial mark, abstract mark, lettermark, wordmark, emblem, mascot, and combination mark.
2. Pick the lead art style independently of the category. Describe the actual drawing qualities, such as cut-paper edges, engraved hatching, brush lettering or geometric construction. Identify what should remain when the artwork is reduced to one color.
3. Screen the initial category and at least one alternative against the audience, motif, and first placement. Record fit and a reason for each. The shortlist can favor an alternative category when it fits better.
4. Write at least three distinct concept examples that use fitting categories. For each, describe what would be drawn, how it connects to the brand, and one trade-off at its intended size. Link any outside visual references with the element being studied. Written examples and source references give the owner a comparison before new artwork is generated.
5. Score every concept from 1 to 5 on each criterion. Use 1 for weak, 3 for workable, and 5 for strong. Record a short reason with each scorecard.

| Criterion | Weight | What to assess |
| --- | --- | --- |
| Brand fit | 35% | Connection to the product and audience |
| Artistic character | 25% | Evidence of craft, visual character, and an intentional style |
| Distinctiveness | 25% | Recall and distance from obvious category clichés or recognizable marks |
| Versatility | 15% | One-color silhouette, small-size legibility, and plausible lockup |

The total out of 100 is the sum of each score multiplied by its weight and divided by five. Select one concept with the highest total. Record the deciding criterion when totals tie. If feedback changes the lead, update the ratings or shortlist and explain the decision.

## Name confirmation

Present the shortlist, ratings and selected concept first. Then ask whether the exact product name and the exact text in the wordmark are locked. If the owner gives a correction, update the strings and get an explicit confirmation on the revised spelling and casing. A negative or ambiguous answer leaves the design pending. Record only a publishable decision reference in a public kit.

Copy the confirmed strings into the confirmation object in the [decision record](creative-decision.json). Run `python3 brand-identity/verify.py --ready-for-artwork` before asking @Images to draw. A reusable template and a project whose name is pending remain valid work in progress without new brand artwork.

## Decision record fields

- `initial_category` and `art_style` are nonempty strings. `category_fit` maps each category to a boolean `fits` and a `reason`.
- `concepts` contains objects with an `id`, `category`, `art_style`, `example`, `rationale`, and a `scores` object. The four score keys are `brand_fit`, `artistic_character`, `distinctiveness`, and `versatility`.
- `selected_concept` is the selected ID. `selection_reason` records why it leads.
- `names` is the source for the current exact `product` and `wordmark` strings. Apply each name change here before seeking confirmation. `confirmation` starts as null. Once the owner confirms both strings, set `confirmation.product`, `confirmation.wordmark`, and `confirmation.reference` to the exact names and a publishable decision reference.
- The [asset manifest](../09-assets/manifest.json) can be populated after the decision passes. See [review](../08-review/review.md) for the visual checks and owner decisions.

Continue with the [logo](../04-logo/logo.md), [wordmark](../05-wordmark/wordmark.md), and [visual system](../06-visual-system/system.md).
