# Subproblem 1: Visual Contract

## 1. Goal

Define the exact Reddit-like product surface before any frontend code is written.

The output of this step is a visual contract that implementation and verification can use as the source of truth.

## 2. Why this step exists

Without a visual contract, the new frontend can drift into a generic recommender dashboard. The requested target is specifically the newer Reddit desktop experience shown in the provided screenshot.

## 3. Files involved

- `plan/zhihurec-reddit-product-frontend/01-visual-contract.md` - this source-of-truth visual contract.
- `product-frontend/` - later implementation must follow this contract.
- `docs/v1_local_runbook.md` - later documentation should mention the product frontend visual verification path.

## 4. Exact changes

Use these product and visual decisions:

- The app is a Reddit-like product frontend, not a marketing page.
- The first screen is the feed, not a landing hero.
- Use a three-column desktop layout at `1920x900`:
  - topbar height around `49px`
  - left rail around `268px`
  - center feed around `720-760px`
  - right rail around `300-330px`
- Use a white page background, pale gray side panels, thin gray dividers, and Reddit-like orange `#ff4500`.
- Topbar:
  - left wordmark text is `zhihurec`
  - center search field
  - right compact action icons and persona/avatar
- Left rail:
  - Home
  - Popular
  - Explore
  - Custom Feeds
  - Communities
- Center feed:
  - sort tabs such as Best, New, Hot
  - post cards styled like Reddit feed items
  - community line, title, summary, topic chips, reason line, vote/comment/share actions
- Right rail:
  - Recent Posts
  - active persona/profile summary
  - compact topic-weight/debug preview
- Brand rule:
  - do not use Reddit logo, Reddit wordmark, Reddit mascot, real subreddit names, or copied assets.
  - use Reddit-like layout, spacing, color, and interaction language.

Responsive target:

- At `390x844`, collapse side rails and show the feed without horizontal overflow.
- Text must not overlap, overflow buttons, or hide behind fixed bars.

## 5. Out of scope

- Do not implement frontend code in this step.
- Do not add generated images or icons in this step.
- Do not decide backend API internals in this step.

## 6. Done condition

The visual target, desktop layout, mobile behavior, brand limits, and screenshot verification expectations are clear enough that another engineer can build against them without asking for design direction.

## 7. Verification

Before frontend implementation starts, confirm the plan includes:

- desktop viewport target `1920x900`
- mobile viewport target `390x844`
- no Reddit brand asset usage
- required visible text groups
- screenshot/OCR comparison requirement

## 8. Expected output

This file remains the visual source of truth for the feature.

## 9. Notes for the next step

The next step can assume the product app should look like the provided newer Reddit screenshot while using ZhihuRec-specific branding and recommender content.

## 10. Risks or ambiguity

The main risk is over-copying Reddit brand assets. Keep the visual structure close, but keep identity and content project-owned.
