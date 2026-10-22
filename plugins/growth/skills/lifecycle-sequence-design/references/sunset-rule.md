# Sunset rule

Read this at step 7, when defining engagement and the removal date.

## Contents

- Engagement definition
- The rule
- Checks before removal

## Engagement definition

Count a person as engaged if, within a rolling window, they clicked a link in a message, visited the product or website while signed in, or purchased. Do not count opens. Choose the window to suit the purchase cycle: a few months for a weekly product, longer for annual purchases. Write the window down.

## The rule

1. Mark people with no engagement in the window as inactive.
2. Send the win-back sequence (a few messages, the last one stating that mailing will stop).
3. Anyone who still has no engagement a fixed number of days after the final message is removed from marketing mailings on the stated date.
4. Record removal in the suppression list with the date and reason; do not delete the record.
5. Repeat on a schedule, such as monthly.

## Checks before removal

- Exclude people with an open order, active subscription, pending renewal or open support case, who still need transactional mail (which is unaffected by this rule).
- Confirm clicks from security scanners are not counted as engagement; if a platform reports unusually uniform clicks seconds after sending, filter them.
- Compare the first run's volume with the list size before removing anyone; a large share suggests a tracking fault, not a dormant list.
