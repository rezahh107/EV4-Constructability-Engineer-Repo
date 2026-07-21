# EV4 CE First Run Guide

Canonical startup authority:

```text
manifests/ce-conversation-bootstrap.v1.json
```

## Fast Start

<!-- EV4_CE_BOOTSTRAP_QUICK_START_START -->
```text
1. Create or open the CE ChatGPT Project and load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md` as the Project Instructions.
2. Send the exact normalized message `شروع`.
3. Upload the standalone `ce-input.json` produced by `EV4-Project-Gate / architect-to-ce`.
4. Upload the exact Architect source bundle whose canonical SHA-256 is declared by that CE input.
5. Treat any Receipt-like attachment as `diagnostic_untrusted` until official external Receipt validation succeeds.
6. Never extract nested `result.output`, rebuild CE input manually, or continue on mixed/conflicting attachments.
7. Only successful integrated authorization + intake validation + source binding may route to `architect_intake_validation`.
```
<!-- EV4_CE_BOOTSTRAP_QUICK_START_END -->

## Expected bare-start response

<!-- EV4_CE_BOOTSTRAP_RESPONSE_START -->
```text
EV4 Constructability Engineer آماده است.

برای شروع بررسی Constructability، فایل `ce-input.json` و source bundle دقیق آن را که توسط مسیر `EV4-Project-Gate / architect-to-ce` استفاده شده است ارسال کن.

ورودی باید با قرارداد `ev4-ce-architect-stage-intake@1.1.0` معتبر باشد و binding آن با bytes واقعی source bundle تأیید شود.
فایل `project-gate-a2c-receipt.json` تا اعتبارسنجی رسمی فقط evidence تشخیصیِ غیرقابل‌اعتماد است و جایگزین ورودی CE نیست.

پس از اعتبارسنجی ورودی و source binding، بررسی فقط از مرحله `architect_intake_validation` آغاز می‌شود.
تا پیش از آن، هیچ نتیجه Constructability، استراتژی اجرا یا آمادگی Builder اعلام نمی‌شود.
```
<!-- EV4_CE_BOOTSTRAP_RESPONSE_END -->

## Required files

Upload the standalone `ce-input.json` and the exact Architect source bundle whose canonical SHA-256 is declared in `project_gate_transition.source_bundle_hash`. A Receipt-like file remains `diagnostic_untrusted` until official validation and cannot replace either required artifact.

## What happens next

Only integrated authorization, official intake validation, and successful source binding authorize `architect_intake_validation`. All mixed, ambiguous, missing-binding, invalid-binding, legacy, wrong-stage, or Receipt-only states remain fail-closed.
