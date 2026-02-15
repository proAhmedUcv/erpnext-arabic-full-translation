# Working with locale files (gettext CLI)

Use the official **GNU gettext** tools instead of custom scripts.

## Prerequisites

```bash
# Ubuntu/Debian
sudo apt install gettext

# Verify
msgmerge --version
msgattrib --version
msgcat --version
```

## 1. Extract entries to translate (untranslated only)

From a `.po` file that is already in sync with the template:

```bash
cd arabic_translations/locale/other-apps/v16/frappe/frappe/locale

# Optional: update ar.po with any new strings from main.pot (run from repo root)
msgmerge -U ar.po main.pot

# Extract only untranslated entries → to_translate.po
msgattrib --no-obsolete --untranslated ar.po -o to_translate.po
```

Translate the `msgstr` fields in `to_translate.po` (e.g. save as `translated.po`).

## 2. Merge your translations back into ar.po

After filling in `translated.po`, merge it into `ar.po` (first file wins for duplicate msgids):

```bash
msgcat --use-first translated.po ar.po -o ar_new.po
mv ar_new.po ar.po
```

## One-liner (frappe v16 locale dir)

```bash
LOCALE="arabic_translations/locale/other-apps/v16/frappe/frappe/locale"
msgmerge -U "$LOCALE/ar.po" "$LOCALE/main.pot"
msgattrib --no-obsolete --untranslated "$LOCALE/ar.po" -o "$LOCALE/to_translate.po"
# ... translate to_translate.po → translated.po ...
msgcat --use-first "$LOCALE/translated.po" "$LOCALE/ar.po" -o "$LOCALE/ar_new.po"
mv "$LOCALE/ar_new.po" "$LOCALE/ar.po"
```

Same idea works for `erpnext` or `hrms` by changing the path (e.g. `.../v16/erpnext/erpnext/locale`).

---

**Note:** The custom `scripts/extract_untranslated.py` is no longer needed if you use the gettext CLI above. You can keep it as a fallback when gettext is not installed.
