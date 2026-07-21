# EV4 CE First Run Guide

Canonical startup authority:

```text
manifests/ce-conversation-bootstrap.v1.json
```

## Fast Start

<!-- EV4_CE_BOOTSTRAP_QUICK_START_START -->
```text
1. Create or open the CE ChatGPT Project and load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md` as the Project Instructions.
2. Send `شروع`.
3. Upload the standalone `ce-input.json` produced by `EV4-Project-Gate / architect-to-ce`.
4. Optionally retain or upload `project-gate-a2c-receipt.json` for diagnostics only.
5. Never extract nested `result.output` or rebuild CE input manually.
6. Validation begins at `architect_intake_validation`; bootstrap itself produces no Constructability conclusion.
```
<!-- EV4_CE_BOOTSTRAP_QUICK_START_END -->

## Expected bare-start response

After sending only `شروع` without a usable CE input, the Project must return exactly:

<!-- EV4_CE_BOOTSTRAP_RESPONSE_START -->
```text
EV4 Constructability Engineer آماده است.

برای شروع بررسی Constructability، فایل `ce-input.json` تولیدشده توسط مسیر `EV4-Project-Gate / architect-to-ce` را ارسال کن.

ورودی باید با قرارداد `ev4-ce-architect-stage-intake@1.1.0` معتبر باشد.
فایل `project-gate-a2c-receipt.json` اختیاری و فقط برای بررسی فنی است؛ جایگزین ورودی CE نیست.

پس از دریافت ورودی معتبر، بررسی از مرحله `architect_intake_validation` آغاز می‌شود.
تا پیش از اعتبارسنجی ورودی، هیچ نتیجه Constructability، استراتژی اجرا یا آمادگی Builder اعلام نمی‌شود.
```
<!-- EV4_CE_BOOTSTRAP_RESPONSE_END -->

## Which file to upload

Upload the standalone `ce-input.json` produced by:

```text
EV4-Project-Gate
→ architect-to-ce
→ ce-input.json
```

The file must actually validate as `ev4-ce-architect-stage-intake@1.1.0`. Its filename is only a convenience.

The separately produced `project-gate-a2c-receipt.json` may be retained or uploaded for diagnostics, but it is not CE semantic input and cannot replace `ce-input.json`.

Never manually extract nested `result.output`, copy a JSON fragment, or rebuild CE input from a Project Gate envelope or Receipt.

## What happens next

A valid canonical input authorizes only:

```text
architect_intake_validation
```

Invalid, insufficient-evidence, ambiguous, legacy, Receipt-only, or wrong-stage input remains fail-closed. No Constructability conclusion, implementation strategy, Builder package, Builder readiness, Responsive completion, or production readiness exists at bootstrap.
