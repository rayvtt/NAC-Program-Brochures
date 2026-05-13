# Paywall edit — turkey-cbi_8.html

**Date:** 2026-05-06
**Edit type:** Non-destructive wrapping (no original content removed)
**Reason:** Gate sections 4–9 behind email-capture form. First 3 sections remain free.

## What was added

1. **Paywall CSS block** — injected just before `</style>` (was line 501). Adds:
   - `.nac-paywall-wrap` (positioning context)
   - `.nac-paywall-zone` (blur + opacity + pointer-events:none)
   - `.nac-paywall-overlay` (fade-to-white scrim)
   - `.nac-paywall-card` (sticky lock card with form)
   - `.nac-paywall-form` (input + button styling)

2. **Paywall wrapper opened** — inserted between section 3's closing tag and section 4's `<hr class="divider">` (was line 810 area). Includes the lock card with the request form.

3. **Paywall wrapper closed** — inserted after section 9's closing `</section>` (was line 1026 area), before the `</div>` of `.content`.

4. **JS submit handler** — appended just before `</script>` at file end. Submits to Formspree placeholder, shows success state, falls back to mailto on error.

## How to restore

Delete the three injected blocks (CSS, wrapper open, wrapper close, JS handler). All original sections 1–9 are preserved verbatim inside the wrapper.

## Formspree placeholder to swap

Search for `FORMSPREE_FORM_ID_HERE` in the file and replace with the real form ID once configured.
