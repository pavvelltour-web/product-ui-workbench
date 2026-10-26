# Retained actual shadcn/Radix component sources

Ten retained shadcn/ui TSX source snapshots are distributed under their upstream MIT notice. Exact file hashes and API/dependency metadata accompany the files. The upstream commit is unknown; a retained snapshot is not a fresh registry call, MCP connection or consuming-application verification.

Copy `ui/` into the project's configured `@/components/ui` location. Preserve `LICENSE.md`, source hashes and dependency pins. The source uses **`cn` from the `cn` package**, `radix-ui` consolidated primitives, `lucide-react`, and `class-variance-authority`; it does not require a fabricated `lib/utils.ts`. `DialogFooter` imports Button through `@/components/ui/button`. Install/build decisions remain subject to actual project authorization. Tailwind4 semantic CSS tokens (`background`, `foreground`, `primary`, `muted`, `border`, `input`, `ring`, `popover`, etc.) and animation utilities must be defined in the host app; source copies alone are not a styled running application.

| Item | Actual source contract | States/semantics to verify in consuming app |
|---|---|---|
| Button | Native button props + `variant`, `size`, `asChild`; `Slot.Root` when asChild; exports `buttonVariants` | native keyboard, disabled, invalid, focus; asChild child semantics |
| Dialog | Root/Trigger/Portal/Close/Overlay/Content/Title/Description/Header/Footer; Content `showCloseButton=true`; Footer optional close Button | Radix controlled `open/onOpenChange` or uncontrolled; focus trap/return, Escape, labeled title/description; async recovery owned by app |
| Input | `React.ComponentProps<"input">`; type/className forwarded | native validation/input types, accessible label and error linkage |
| Tabs | Radix Root/Content/Trigger; Root orientation; List `variant=default|line`, exports list variants | controlled value or defaultValue, keyboard orientation, selected panel |
| Select | Radix Root/Trigger/Value/Content/Group/Item/Label/Separator/scroll buttons; Trigger size; Content position/align | controlled value/onValueChange or defaultValue, portal keyboard/typeahead, labels/errors |
| Tooltip | Provider default delay0; Root/Trigger/Content; Content sideOffset0 | nonessential supporting info only; keyboard/focus/touch discoverability and accessible names remain product responsibilities |
| Badge | Native span props + variant/asChild; Slot.Root optional | label semantics; not a button without a suitable child |
| Checkbox | Radix Root+Indicator; primitive checked/defaultChecked/onCheckedChange | Boolean/indeterminate behavior, Space, accessible label; selection universe owned by app |
| Textarea | native textarea props, className forwarded | labels, value/onChange, long text, errors, recovery owned by app |
| Separator | Radix Root; orientation horizontal by default; decorative true | set decorative=false only when semantically appropriate |

No upstream API extraction is claimed beyond inspected TSX. Current default size4 Checkbox is a visual control size, not a claim of a universal touch target; the app must provide suitable surrounding target/spacing. The MIT notice applies to these retained upstream component sources, not private reference pixels or all dependency packages.
