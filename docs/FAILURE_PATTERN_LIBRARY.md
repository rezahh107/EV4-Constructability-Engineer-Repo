# Failure Pattern Library MVP

## FP-01 geometry_dependency_not_proven

Connector lines, arrows, visual relationships, and decorative overlays between elements require source anchors, target anchors, geometry strategy, and repair policy.

## FP-02 asset_dependency_not_proven

Image, SVG, icon, or background assets require source file, URL, or explicit placeholder policy.

## FP-03 overlay_strategy_not_proven

Absolute, fixed, decorative, or z-index-dependent layers require containment parent, positioning model, z-index model, and overflow policy.

## FP-04 responsive_behavior_implied_not_defined

Mobile, tablet, breakpoint, or responsive typography actions require evidence-backed strategy or explicit block. Desktop-only work may continue only when responsive actions are blocked.

## FP-05 interaction_implied_not_confirmed

Interactive cards, hover states, tabs, accordions, and toggles require approved behavior and handler or target definition.

## FP-06 dynamic_loop_not_approved

Repeated elements must not be converted into Dynamic Loop or data binding unless explicitly approved and mapped.

## FP-07 accessibility_claim_without_evidence

Accessibility, semantic, ARIA, keyboard, focus, or WCAG claims require supporting evidence.

## FP-08 ui_control_path_uncertainty

Exact Elementor UI control paths require current UI screenshot, user statement, installed version evidence, or official documentation.
