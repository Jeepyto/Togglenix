from __future__ import annotations

import locale
import os

STRINGS: dict[str, dict[str, str]] = {
    "fr": {
        "app_title": "Togglenix",
        "tab_categories": "Catégories",
        "tab_modules": "Modules",
        "tab_edit": "Modification",
        "tooltip_add": "Ajouter un module",
        "tooltip_refresh": "Recharger l'état depuis les fichiers",
        "tooltip_prefs": "Préférences (chemin du repo)",
        "tooltip_theme": "Basculer thème clair / sombre",
        "tooltip_language": "Changer la langue (FR/EN)",
        "tooltip_edit_module": "Modifier ce module",
        "tooltip_delete_module": "Supprimer ce module",
        "placeholder_no_modules_title": "Aucun module configuré",
        "placeholder_no_modules_desc": "Utilise le bouton + en haut pour ajouter ton premier module.",
        "placeholder_no_categories_title": "Aucune catégorie",
        "placeholder_no_categories_desc": "Ajoute des modules dans l'onglet Modules pour voir leurs catégories apparaître ici.",
        "categories_group_desc": "Active ou désactive tous les modules d'une catégorie en une fois.",
        "module_count_singular": "{n} module",
        "module_count_plural": "{n} modules",
        "module_count_error_suffix": " — certains ont une erreur de lecture",
        "toast_module_added": "Module « {name} » ajouté.",
        "toast_module_updated": "Module « {name} » modifié.",
        "toast_module_deleted": "Module « {name} » supprimé.",
        "toast_module_not_found": "Module introuvable (déjà modifié ailleurs ?).",
        "toast_module_already_deleted": "Module déjà supprimé.",
        "toast_module_error": "Erreur sur « {name} » : {error}",
        "toast_module_toggled": "{name} {state}. N'oublie pas d'appliquer.",
        "state_enabled": "activé",
        "state_disabled": "désactivé",
        "toast_category_toggled": "Catégorie « {category} » {state} ({n} module(s)). N'oublie pas d'appliquer.",
        "category_state_enabled": "activée",
        "category_state_disabled": "désactivée",
        "toast_category_error": "Erreur sur {n} module(s) de « {category} » : {details}",
        "toast_prefs_saved": "Préférences enregistrées.",
        "toast_prefs_empty_path": "Le chemin ne peut pas être vide.",
        "toast_reset_done": "Liste des modules réinitialisée.",
        "toast_apply_opening": "Ouverture d'un terminal pour nixos-rebuild — regarde la fenêtre qui vient de s'ouvrir.",
        "toast_apply_no_terminal": "Aucun émulateur de terminal trouvé parmi : {tried}. Lance la commande toi-même dans un terminal.",
        "toast_apply_terminal_failed": "{binary} trouvé mais a échoué à démarrer : {error}",
        "toast_apply_terminal_opened": "Terminal ouvert ({binary}) — suis la progression du rebuild dans cette fenêtre, puis clique sur Recharger ici une fois terminé.",
        "dialog_add_title": "Ajouter un module",
        "dialog_edit_title": "Modifier le module",
        "dialog_prefs_title": "Préférences",
        "btn_cancel": "Annuler",
        "btn_add": "Ajouter",
        "btn_save": "Enregistrer",
        "btn_reset_json": "Reset JSON",
        "field_name": "Nom affiché",
        "field_category": "Catégorie",
        "field_default_category": "Autres",
        "field_file": "Fichier default.nix (relatif à la racine)",
        "field_file_tooltip": "Chemin complet vers le fichier default.nix qui contient le bloc imports = [ ... ]; — pas juste le dossier.\nEx: modules/home-manager/jeepyto/applications/communication/default.nix",
        "field_target": "Chemin importé (ex: ./realvnc)",
        "form_desc": "Le module sera (dés)activé en commentant/décommentant sa ligne dans le bloc imports = [ ... ]; du fichier indiqué.",
        "validation_name_file_required": "Nom et fichier sont obligatoires.",
        "validation_target_required": "Le chemin importé est obligatoire (ex: ./realvnc).",
        "prefs_root_group_title": "Racine du dépôt",
        "prefs_root_group_desc": "Chemin absolu vers ton repo NixOS-Config (ex: /home/jeepyto/Projets/NixOS-Config)",
        "prefs_root_path_label": "root_path",
        "prefs_scan_group_title": "Découverte automatique",
        "prefs_scan_group_desc": "Cherche dans ton repo tous les default.nix avec des modules importables, sans rien modifier.",
        "prefs_scan_label": "Scanner mon repo",
        "btn_scan": "Scanner",
        "dialog_scan_title": "Modules trouvés",
        "scan_no_results_title": "Rien trouvé",
        "scan_no_results_desc": "Aucun fichier default.nix avec un import reconnaissable n'a été trouvé sous root_path.",
        "scan_select_all": "Tout cocher",
        "scan_select_none": "Tout décocher",
        "btn_import_selection": "Importer la sélection",
        "toast_scan_error": "Erreur pendant le scan : {error}",
        "toast_scan_imported": "{n} module(s) importé(s).",
        "toast_scan_none_selected": "Aucun module coché.",
        "scan_already_exists_suffix": " (déjà dans ta liste)",
        "prefs_danger_title": "Zone de danger",
        "prefs_danger_desc": "Si ta structure de modules ne correspond pas à celle préconfigurée, repars d'une liste vide.",
        "prefs_reset_label": "Réinitialiser la liste des modules",
        "confirm_delete_title": "Supprimer « {name} » ?",
        "confirm_delete_body": "Le module sera retiré de ta liste Togglenix. Le fichier .nix correspondant n'est pas modifié.",
        "confirm_reset_title": "Réinitialiser la liste des modules ?",
        "confirm_reset_body": "Tous les modules ajoutés seront supprimés. root_path sera conservé. Cette action est irréversible.",
        "btn_delete": "Supprimer",
        "btn_reset": "Réinitialiser",
        "apply_btn_label": "Appliquer (nixos-rebuild)",
    },
    "en": {
        "app_title": "Togglenix",
        "tab_categories": "Categories",
        "tab_modules": "Modules",
        "tab_edit": "Edit",
        "tooltip_add": "Add a module",
        "tooltip_refresh": "Reload state from files",
        "tooltip_prefs": "Preferences (repo path)",
        "tooltip_theme": "Toggle light / dark theme",
        "tooltip_language": "Change language (FR/EN)",
        "tooltip_edit_module": "Edit this module",
        "tooltip_delete_module": "Delete this module",
        "placeholder_no_modules_title": "No modules configured",
        "placeholder_no_modules_desc": "Use the + button at the top to add your first module.",
        "placeholder_no_categories_title": "No categories",
        "placeholder_no_categories_desc": "Add modules in the Modules tab to see their categories appear here.",
        "categories_group_desc": "Enable or disable all modules in a category at once.",
        "module_count_singular": "{n} module",
        "module_count_plural": "{n} modules",
        "module_count_error_suffix": " — some have a read error",
        "toast_module_added": "Module '{name}' added.",
        "toast_module_updated": "Module '{name}' updated.",
        "toast_module_deleted": "Module '{name}' deleted.",
        "toast_module_not_found": "Module not found (already modified elsewhere?).",
        "toast_module_already_deleted": "Module already deleted.",
        "toast_module_error": "Error on '{name}': {error}",
        "toast_module_toggled": "{name} {state}. Don't forget to apply.",
        "state_enabled": "enabled",
        "state_disabled": "disabled",
        "toast_category_toggled": "Category '{category}' {state} ({n} module(s)). Don't forget to apply.",
        "category_state_enabled": "enabled",
        "category_state_disabled": "disabled",
        "toast_category_error": "Error on {n} module(s) in '{category}': {details}",
        "toast_prefs_saved": "Preferences saved.",
        "toast_prefs_empty_path": "The path cannot be empty.",
        "toast_reset_done": "Module list reset.",
        "toast_apply_opening": "Opening a terminal for nixos-rebuild — check the window that just opened.",
        "toast_apply_no_terminal": "No terminal emulator found among: {tried}. Run the command yourself in a terminal.",
        "toast_apply_terminal_failed": "{binary} found but failed to start: {error}",
        "toast_apply_terminal_opened": "Terminal opened ({binary}) — follow the rebuild progress in that window, then click Reload here once it's done.",
        "dialog_add_title": "Add a module",
        "dialog_edit_title": "Edit module",
        "dialog_prefs_title": "Preferences",
        "btn_cancel": "Cancel",
        "btn_add": "Add",
        "btn_save": "Save",
        "btn_reset_json": "Reset JSON",
        "field_name": "Display name",
        "field_category": "Category",
        "field_default_category": "Other",
        "field_file": "default.nix file (relative to root)",
        "field_file_tooltip": "Full path to the default.nix file that contains the imports = [ ... ]; block — not just the folder.\nEx: modules/home-manager/jeepyto/applications/communication/default.nix",
        "field_target": "Imported path (e.g. ./realvnc)",
        "form_desc": "The module will be enabled/disabled by commenting/uncommenting its line inside the imports = [ ... ]; block of the given file.",
        "validation_name_file_required": "Name and file are required.",
        "validation_target_required": "The imported path is required (e.g. ./realvnc).",
        "prefs_root_group_title": "Repository root",
        "prefs_root_group_desc": "Absolute path to your NixOS-Config repo (e.g. /home/jeepyto/Projects/NixOS-Config)",
        "prefs_root_path_label": "root_path",
        "prefs_scan_group_title": "Automatic discovery",
        "prefs_scan_group_desc": "Searches your repo for every default.nix with importable modules, without modifying anything.",
        "prefs_scan_label": "Scan my repo",
        "btn_scan": "Scan",
        "dialog_scan_title": "Modules found",
        "scan_no_results_title": "Nothing found",
        "scan_no_results_desc": "No default.nix file with a recognizable import was found under root_path.",
        "scan_select_all": "Select all",
        "scan_select_none": "Select none",
        "btn_import_selection": "Import selection",
        "toast_scan_error": "Error during scan: {error}",
        "toast_scan_imported": "{n} module(s) imported.",
        "toast_scan_none_selected": "No module selected.",
        "scan_already_exists_suffix": " (already in your list)",
        "prefs_danger_title": "Danger zone",
        "prefs_danger_desc": "If your module structure doesn't match the preconfigured one, start over from an empty list.",
        "prefs_reset_label": "Reset the module list",
        "confirm_delete_title": "Delete '{name}'?",
        "confirm_delete_body": "The module will be removed from your Togglenix list. The corresponding .nix file is not modified.",
        "confirm_reset_title": "Reset the module list?",
        "confirm_reset_body": "All added modules will be deleted. root_path will be kept. This action is irreversible.",
        "btn_delete": "Delete",
        "btn_reset": "Reset",
        "apply_btn_label": "Apply (nixos-rebuild)",
    },
}

DEFAULT_CATEGORY_KEY = "field_default_category"


def detect_system_language() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value and value.lower().startswith("fr"):
            return "fr"
        if value and value.lower().startswith("en"):
            return "en"

    try:
        lang_code, _ = locale.getlocale()
        if lang_code and lang_code.lower().startswith("fr"):
            return "fr"
    except (ValueError, locale.Error):
        pass

    return "en"


def resolve_language(language_setting: str) -> str:
    if language_setting in ("fr", "en"):
        return language_setting
    return detect_system_language()


class Translator:
    def __init__(self, language_setting: str = "auto"):
        self.set_language(language_setting)

    def set_language(self, language_setting: str) -> None:
        self.effective_language = resolve_language(language_setting)

    def tr(self, key: str, **kwargs) -> str:
        table = STRINGS.get(self.effective_language, STRINGS["en"])
        template = table.get(key) or STRINGS["en"].get(key, key)
        if kwargs:
            return template.format(**kwargs)
        return template
