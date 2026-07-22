# EV4 CE First Run Guide — Lean Runtime

## هدف

اجرای CE باید با کمترین اصطکاک و بدون حذف کنترل‌های correctness انجام شود.

## شروع

فایل CE input معتبر را مستقیماً ارسال کن:

```text
ev4-ce-architect-stage-intake@1.1.0
```

ارسال `شروع` قبل از فایل اختیاری است. این عبارت مجوز امنیتی نیست.

## فایل‌های اضافی

- Receipt، فایل‌های قدیمی، فایل‌های نامرتبط و JSONهای اضافی در کنار یک CE input معتبر فقط warning هستند.
- تنها وجود چند CE input معتبر، انتخاب خودکار را متوقف می‌کند.
- فایل source bundle فقط وقتی لازم است که CE یک ابهام مشخص درباره هویت، تصمیم یا جزئیات اجرا گزارش کند.
- اگر source bundle برای تصمیم استفاده شود، bytes، hash، identity، transition و provenance آن بررسی می‌شود.

## جریان اجرا

```text
INTAKE_VALIDATING
→ REVIEW_ACTIVE
→ STRATEGY_READY
→ EXPORT_VALIDATING
→ COMPLETED
```

وقتی مدرک لازم کم باشد:

```text
EVIDENCE_REQUIRED
```

CE باید دقیقاً بگوید چه evidenceای لازم است و چرا.

## Builder-ready

CE تا وقتی blocking dependencies، تصمیم راهبردی حل‌نشده، implementation strategy ناقص، فیلد اجباری مفقود یا خطای schema وجود دارد، خروجی را Builder-ready اعلام نمی‌کند.

## Export

خروجی باید deterministic، schema-valid و atomic باشد. artifact نامعتبر منتشر نمی‌شود.

## Repository Maintenance

درخواست‌های code، test، CI، schema، PR و documentation وارد `repository_maintenance` می‌شوند و CE runtime را شروع نمی‌کنند.

## Controlled Quick Start

1. Load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md`.
2. Send the valid `ce-input.json`; sending `شروع` first is optional.
3. Add a source bundle only when CE reports a concrete evidence requirement.
4. Extra unrelated files are warnings, not runtime blockers.
5. CE blocks only invalid/insufficient CE input, multiple valid CE inputs, or relevant evidence that contradicts the selected input.
6. Builder-ready remains impossible while dependencies, strategy decisions, required fields, or validation errors remain.
