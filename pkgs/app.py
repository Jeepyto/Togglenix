from __future__ import annotations

import shutil
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gio, Gtk

from core import (
    AppConfig,
    ModuleEntry,
    ScanResult,
    ToggleError,
    read_state,
    scan_default_nix_files,
    set_state,
)
from i18n import Translator

APP_ID = "com.jeepyto.Togglenix"


class CategoryRow(Adw.ActionRow):
    def __init__(self, category: str, entries: list[ModuleEntry], app_window: "MainWindow"):
        super().__init__()
        self.category = category
        self.entries = entries
        self.app_window = app_window
        tr = app_window.translator.tr

        self.set_title(category)
        count = len(entries)
        count_key = "module_count_singular" if count == 1 else "module_count_plural"
        self.set_subtitle(tr(count_key, n=count))

        self.switch = Gtk.Switch()
        self.switch.set_valign(Gtk.Align.CENTER)
        self.add_suffix(self.switch)
        self.set_activatable_widget(self.switch)

        self._load_state()

        self.switch.connect("state-set", self._on_switch_toggled)

    def _load_state(self) -> None:
        tr = self.app_window.translator.tr
        any_active = False
        any_error = False
        for entry in self.entries:
            try:
                if read_state(self.app_window.config.root_path, entry):
                    any_active = True
            except ToggleError:
                any_error = True

        self.switch.set_active(any_active)
        count = len(self.entries)
        count_key = "module_count_singular" if count == 1 else "module_count_plural"
        if any_error:
            self.add_css_class("error")
            self.set_subtitle(tr(count_key, n=count) + tr("module_count_error_suffix"))
        else:
            self.remove_css_class("error")

    def _on_switch_toggled(self, switch: Gtk.Switch, state: bool) -> bool:
        tr = self.app_window.translator.tr
        errors: list[str] = []
        for entry in self.entries:
            try:
                set_state(self.app_window.config.root_path, entry, enabled=state)
            except ToggleError as exc:
                errors.append(f"{entry.name}: {exc}")

        if errors:
            self.app_window.show_toast(
                tr(
                    "toast_category_error",
                    n=len(errors),
                    category=self.category,
                    details="; ".join(errors[:2]) + ("…" if len(errors) > 2 else ""),
                )
            )
            self.add_css_class("error")
        else:
            self.remove_css_class("error")
            state_key = "category_state_enabled" if state else "category_state_disabled"
            self.app_window.show_toast(
                tr(
                    "toast_category_toggled",
                    category=self.category,
                    state=tr(state_key),
                    n=len(self.entries),
                )
            )
            self.app_window._dirty = True

        GLib.idle_add(self.app_window.reload)
        return False


class ModuleRow(Adw.ActionRow):
    def __init__(self, entry: ModuleEntry, app_window: "MainWindow", edit_mode: bool = False):
        super().__init__()
        self.entry = entry
        self.app_window = app_window
        self.edit_mode = edit_mode
        tr = app_window.translator.tr

        self.set_title(entry.name)
        self.set_subtitle(entry.file)

        if edit_mode:
            edit_btn = Gtk.Button(icon_name="document-edit-symbolic")
            edit_btn.set_valign(Gtk.Align.CENTER)
            edit_btn.set_tooltip_text(tr("tooltip_edit_module"))
            edit_btn.connect("clicked", self._on_edit_clicked)
            self.add_suffix(edit_btn)

            delete_btn = Gtk.Button(icon_name="user-trash-symbolic")
            delete_btn.set_valign(Gtk.Align.CENTER)
            delete_btn.add_css_class("destructive-action")
            delete_btn.set_tooltip_text(tr("tooltip_delete_module"))
            delete_btn.connect("clicked", self._on_delete_clicked)
            self.add_suffix(delete_btn)
        else:
            self.switch = Gtk.Switch()
            self.switch.set_valign(Gtk.Align.CENTER)
            self.add_suffix(self.switch)
            self.set_activatable_widget(self.switch)

            self._load_state()

            self.switch.connect("state-set", self._on_switch_toggled)

    def _load_state(self) -> None:
        try:
            state = read_state(self.app_window.config.root_path, self.entry)
            self.switch.set_active(state)
            self.set_sensitive(True)
            self.remove_css_class("error")
        except ToggleError as exc:
            self.switch.set_sensitive(False)
            self.add_css_class("error")
            self.set_subtitle(str(exc))

    def _on_switch_toggled(self, switch: Gtk.Switch, state: bool) -> bool:
        tr = self.app_window.translator.tr
        try:
            set_state(self.app_window.config.root_path, self.entry, enabled=state)
            self.app_window.mark_dirty(self.entry.name, state)
            self.remove_css_class("error")
        except ToggleError as exc:
            self.app_window.show_toast(tr("toast_module_error", name=self.entry.name, error=str(exc)))
            self.add_css_class("error")
            return True
        return False

    def _on_edit_clicked(self, *_args) -> None:
        dialog = EditModuleDialog(self.app_window, self.entry)
        dialog.present()

    def _on_delete_clicked(self, *_args) -> None:
        tr = self.app_window.translator.tr
        confirm = Adw.AlertDialog(
            heading=tr("confirm_delete_title", name=self.entry.name),
            body=tr("confirm_delete_body"),
        )
        confirm.add_response("cancel", tr("btn_cancel"))
        confirm.add_response("delete", tr("btn_delete"))
        confirm.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        confirm.set_default_response("cancel")
        confirm.set_close_response("cancel")
        confirm.connect("response", self._on_delete_confirmed)
        confirm.present(self.app_window)

    def _on_delete_confirmed(self, dialog: Adw.AlertDialog, response: str) -> None:
        if response != "delete":
            return
        self.app_window.remove_module(self.entry)


class PreferencesDialog(Adw.Window):
    def __init__(self, app_window: "MainWindow"):
        tr = app_window.translator.tr
        super().__init__(title=tr("dialog_prefs_title"))
        self.app_window = app_window
        self.set_default_size(680, 560)
        self.set_modal(True)
        self.set_transient_for(app_window)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        cancel_btn = Gtk.Button(label=tr("btn_cancel"))
        cancel_btn.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label=tr("btn_save"))
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        header.pack_end(save_btn)

        page = Adw.PreferencesPage()

        group = Adw.PreferencesGroup(
            title=tr("prefs_root_group_title"),
            description=tr("prefs_root_group_desc"),
        )
        page.add(group)

        self.root_path_row = Adw.EntryRow(title=tr("prefs_root_path_label"))
        self.root_path_row.set_text(app_window.config.root_path)
        group.add(self.root_path_row)

        scan_group = Adw.PreferencesGroup(
            title=tr("prefs_scan_group_title"),
            description=tr("prefs_scan_group_desc"),
        )
        page.add(scan_group)

        scan_row = Adw.ActionRow(title=tr("prefs_scan_label"))
        scan_btn = Gtk.Button(label=tr("btn_scan"))
        scan_btn.set_valign(Gtk.Align.CENTER)
        scan_btn.connect("clicked", self._on_scan_clicked)
        scan_row.add_suffix(scan_btn)
        scan_group.add(scan_row)

        danger_group = Adw.PreferencesGroup(
            title=tr("prefs_danger_title"),
            description=tr("prefs_danger_desc"),
        )
        page.add(danger_group)

        reset_row = Adw.ActionRow(title=tr("prefs_reset_label"))
        reset_btn = Gtk.Button(label=tr("btn_reset_json"))
        reset_btn.add_css_class("destructive-action")
        reset_btn.set_valign(Gtk.Align.CENTER)
        reset_btn.connect("clicked", self._on_reset_clicked)
        reset_row.add_suffix(reset_btn)
        danger_group.add(reset_row)

        toolbar_view.set_content(page)
        self.set_content(toolbar_view)

    def _on_scan_clicked(self, *_args) -> None:
        root_path = self.root_path_row.get_text().strip() or self.app_window.config.root_path
        dialog = ScanDialog(self.app_window, root_path)
        dialog.present()

    def _on_reset_clicked(self, *_args) -> None:
        tr = self.app_window.translator.tr
        confirm = Adw.AlertDialog(
            heading=tr("confirm_reset_title"),
            body=tr("confirm_reset_body"),
        )
        confirm.add_response("cancel", tr("btn_cancel"))
        confirm.add_response("reset", tr("btn_reset"))
        confirm.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        confirm.set_default_response("cancel")
        confirm.set_close_response("cancel")
        confirm.connect("response", self._on_reset_confirmed)
        confirm.present(self)

    def _on_reset_confirmed(self, dialog: Adw.AlertDialog, response: str) -> None:
        if response != "reset":
            return
        tr = self.app_window.translator.tr
        self.app_window.config.modules = []
        self.app_window.config.save()
        GLib.idle_add(self.app_window.reload)
        self.app_window.show_toast(tr("toast_reset_done"))

    def _on_save_clicked(self, *_args) -> None:
        tr = self.app_window.translator.tr
        new_path = self.root_path_row.get_text().strip()
        if not new_path:
            self.app_window.show_toast(tr("toast_prefs_empty_path"))
            return

        self.app_window.config.root_path = new_path
        self.app_window.config.save()
        GLib.idle_add(self.app_window.reload)
        self.app_window.show_toast(tr("toast_prefs_saved"))
        self.close()


class ScanDialog(Adw.Window):
    def __init__(self, app_window: "MainWindow", root_path: str):
        tr = app_window.translator.tr
        super().__init__(title=tr("dialog_scan_title"))
        self.app_window = app_window
        self.root_path = root_path
        self.set_default_size(680, 620)
        self.set_modal(True)
        self.set_transient_for(app_window)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        cancel_btn = Gtk.Button(label=tr("btn_cancel"))
        cancel_btn.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel_btn)

        self.import_btn = Gtk.Button(label=tr("btn_import_selection"))
        self.import_btn.add_css_class("suggested-action")
        self.import_btn.connect("clicked", self._on_import_clicked)
        header.pack_end(self.import_btn)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.content_box.set_margin_top(18)
        self.content_box.set_margin_bottom(18)
        self.content_box.set_margin_start(18)
        self.content_box.set_margin_end(18)
        self.scrolled.set_child(self.content_box)

        toolbar_view.set_content(self.scrolled)
        self.set_content(toolbar_view)

        self.checkbox_rows: list[tuple[Gtk.CheckButton, ScanResult]] = []
        self._run_scan()

    def _existing_targets(self) -> set[tuple[str, str]]:
        return {(m.file, m.target) for m in self.app_window.config.modules}

    def _run_scan(self) -> None:
        tr = self.app_window.translator.tr
        try:
            top_level = scan_default_nix_files(self.root_path)
        except ToggleError as exc:
            self.app_window.show_toast(tr("toast_scan_error", error=str(exc)))
            self.close()
            return

        if not top_level:
            placeholder = Adw.StatusPage(
                title=tr("scan_no_results_title"),
                description=tr("scan_no_results_desc"),
                icon_name="folder-symbolic",
            )
            self.content_box.append(placeholder)
            self.import_btn.set_sensitive(False)
            return

        select_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        select_all_btn = Gtk.Button(label=tr("scan_select_all"))
        select_all_btn.connect("clicked", lambda *_: self._set_all_checked(True))
        select_row.append(select_all_btn)
        select_none_btn = Gtk.Button(label=tr("scan_select_none"))
        select_none_btn.connect("clicked", lambda *_: self._set_all_checked(False))
        select_row.append(select_none_btn)
        self.content_box.append(select_row)

        existing = self._existing_targets()

        by_file: dict[str, list[ScanResult]] = {}
        for r in top_level:
            by_file.setdefault(r.file, []).append(r)

        for file_path in sorted(by_file.keys()):
            group = Adw.PreferencesGroup(title=file_path)
            list_box = Gtk.ListBox()
            list_box.set_selection_mode(Gtk.SelectionMode.NONE)
            list_box.add_css_class("boxed-list")

            for result in by_file[file_path]:
                widget = self._build_result_widget(result, existing)
                list_box.append(widget)

            group.add(list_box)
            self.content_box.append(group)

    def _build_result_widget(self, result: ScanResult, existing: set[tuple[str, str]]) -> Adw.ActionRow:
        tr = self.app_window.translator.tr

        checkbox = Gtk.CheckButton()
        checkbox.set_valign(Gtk.Align.CENTER)
        already_exists = (result.file, result.target) in existing
        checkbox.set_active(not already_exists)
        checkbox.set_sensitive(not already_exists)
        self.checkbox_rows.append((checkbox, result))

        subtitle = f"{result.target} · {result.suggested_category}"
        if already_exists:
            subtitle += tr("scan_already_exists_suffix")

        row = Adw.ActionRow(title=result.suggested_name)
        row.set_subtitle(subtitle)
        row.add_prefix(checkbox)
        row.set_activatable_widget(checkbox)
        return row

    def _set_all_checked(self, checked: bool) -> None:
        for checkbox, _result in self.checkbox_rows:
            if checkbox.get_sensitive():
                checkbox.set_active(checked)

    def _on_import_clicked(self, *_args) -> None:
        tr = self.app_window.translator.tr
        selected = [result for checkbox, result in self.checkbox_rows if checkbox.get_active()]

        if not selected:
            self.app_window.show_toast(tr("toast_scan_none_selected"))
            return

        imported = 0
        for result in selected:
            try:
                entry = ModuleEntry(
                    name=result.suggested_name,
                    mode="import",
                    file=result.file,
                    target=result.target,
                    category=result.suggested_category,
                    inverted=result.inverted,
                )
            except ToggleError:
                continue
            self.app_window.config.modules.append(entry)
            imported += 1

        self.app_window.config.save()
        GLib.idle_add(self.app_window.reload)
        self.app_window.show_toast(tr("toast_scan_imported", n=imported))
        self.close()


class AddModuleDialog(Adw.Window):
    def __init__(self, app_window: "MainWindow"):
        tr = app_window.translator.tr
        super().__init__(title=tr("dialog_add_title"))
        self.app_window = app_window
        self.set_default_size(680, 560)
        self.set_modal(True)
        self.set_transient_for(app_window)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        cancel_btn = Gtk.Button(label=tr("btn_cancel"))
        cancel_btn.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel_btn)

        add_btn = Gtk.Button(label=tr("btn_add"))
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_end(add_btn)

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(description=tr("form_desc"))
        page.add(group)

        self.name_row = Adw.EntryRow(title=tr("field_name"))
        group.add(self.name_row)

        self.category_row = Adw.EntryRow(title=tr("field_category"))
        self.category_row.set_text(tr("field_default_category"))
        group.add(self.category_row)

        self.file_row = Adw.EntryRow(title=tr("field_file"))
        self.file_row.set_text("modules/")
        self.file_row.set_tooltip_text(tr("field_file_tooltip"))
        group.add(self.file_row)

        self.target_row = Adw.EntryRow(title=tr("field_target"))
        group.add(self.target_row)

        toolbar_view.set_content(page)
        self.set_content(toolbar_view)

    def _on_add_clicked(self, *_args) -> None:
        tr = self.app_window.translator.tr
        name = self.name_row.get_text().strip()
        category = self.category_row.get_text().strip() or tr("field_default_category")
        file_ = self.file_row.get_text().strip()
        target = self.target_row.get_text().strip()

        if not name or not file_:
            self.app_window.show_toast(tr("validation_name_file_required"))
            return
        if not target:
            self.app_window.show_toast(tr("validation_target_required"))
            return

        try:
            entry = ModuleEntry(
                name=name,
                mode="import",
                file=file_,
                target=target,
                category=category,
            )
        except ToggleError as exc:
            self.app_window.show_toast(str(exc))
            return

        self.app_window.add_module(entry)
        self.close()


class EditModuleDialog(Adw.Window):
    def __init__(self, app_window: "MainWindow", entry: ModuleEntry):
        tr = app_window.translator.tr
        super().__init__(title=tr("dialog_edit_title"))
        self.app_window = app_window
        self.original_entry = entry
        self.set_default_size(680, 560)
        self.set_modal(True)
        self.set_transient_for(app_window)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        cancel_btn = Gtk.Button(label=tr("btn_cancel"))
        cancel_btn.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label=tr("btn_save"))
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        header.pack_end(save_btn)

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(description=tr("form_desc"))
        page.add(group)

        self.name_row = Adw.EntryRow(title=tr("field_name"))
        self.name_row.set_text(entry.name)
        group.add(self.name_row)

        self.category_row = Adw.EntryRow(title=tr("field_category"))
        self.category_row.set_text(entry.category)
        group.add(self.category_row)

        self.file_row = Adw.EntryRow(title=tr("field_file"))
        self.file_row.set_text(entry.file)
        self.file_row.set_tooltip_text(tr("field_file_tooltip"))
        group.add(self.file_row)

        self.target_row = Adw.EntryRow(title=tr("field_target"))
        self.target_row.set_text(entry.target or "")
        group.add(self.target_row)

        toolbar_view.set_content(page)
        self.set_content(toolbar_view)

    def _on_save_clicked(self, *_args) -> None:
        tr = self.app_window.translator.tr
        name = self.name_row.get_text().strip()
        category = self.category_row.get_text().strip() or tr("field_default_category")
        file_ = self.file_row.get_text().strip()
        target = self.target_row.get_text().strip()

        if not name or not file_:
            self.app_window.show_toast(tr("validation_name_file_required"))
            return
        if not target:
            self.app_window.show_toast(tr("validation_target_required"))
            return

        try:
            updated_entry = ModuleEntry(
                name=name,
                mode="import",
                file=file_,
                target=target,
                category=category,
            )
        except ToggleError as exc:
            self.app_window.show_toast(str(exc))
            return

        self.app_window.update_module(self.original_entry, updated_entry)
        self.close()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        self.config = AppConfig.load()
        self.translator = Translator(self.config.language)
        tr = self.translator.tr

        super().__init__(application=app, title=tr("app_title"))
        self.set_default_size(820, 900)

        self._dirty = False

        self._apply_theme(self.config.theme)

        self.toast_overlay = Adw.ToastOverlay()
        toolbar_view = Adw.ToolbarView()

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.set_tooltip_text(tr("tooltip_add"))
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_start(add_btn)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text(tr("tooltip_refresh"))
        refresh_btn.connect("clicked", lambda *_: self.reload())
        header.pack_start(refresh_btn)

        prefs_btn = Gtk.Button(icon_name="preferences-system-symbolic")
        prefs_btn.set_tooltip_text(tr("tooltip_prefs"))
        prefs_btn.connect("clicked", self._on_prefs_clicked)
        header.pack_end(prefs_btn)

        self.theme_btn = Gtk.Button()
        self.theme_btn.set_tooltip_text(tr("tooltip_theme"))
        self.theme_btn.connect("clicked", self._on_theme_toggle_clicked)
        self._update_theme_button_icon()
        header.pack_end(self.theme_btn)

        self.language_btn = Gtk.Button()
        self.language_btn.set_tooltip_text(tr("tooltip_language"))
        self.language_btn.connect("clicked", self._on_language_toggle_clicked)
        self._update_language_button_label()
        header.pack_end(self.language_btn)

        self.view_stack = Adw.ViewStack()

        view_switcher = Adw.ViewSwitcher()
        view_switcher.set_stack(self.view_stack)
        view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(view_switcher)

        self.categories_scrolled = Gtk.ScrolledWindow()
        self.categories_scrolled.set_vexpand(True)
        self.categories_list_box_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=18
        )
        self.categories_list_box_container.set_margin_top(18)
        self.categories_list_box_container.set_margin_bottom(18)
        self.categories_list_box_container.set_margin_start(18)
        self.categories_list_box_container.set_margin_end(18)
        self.categories_scrolled.set_child(self.categories_list_box_container)

        self.categories_page = self.view_stack.add_titled(
            self.categories_scrolled, "categories", tr("tab_categories")
        )
        self.categories_page.set_icon_name("view-grid-symbolic")

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.list_box_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.list_box_container.set_margin_top(18)
        self.list_box_container.set_margin_bottom(18)
        self.list_box_container.set_margin_start(18)
        self.list_box_container.set_margin_end(18)
        self.scrolled.set_child(self.list_box_container)

        self.modules_page = self.view_stack.add_titled(self.scrolled, "modules", tr("tab_modules"))
        self.modules_page.set_icon_name("view-list-symbolic")

        self.edit_scrolled = Gtk.ScrolledWindow()
        self.edit_scrolled.set_vexpand(True)
        self.edit_list_box_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.edit_list_box_container.set_margin_top(18)
        self.edit_list_box_container.set_margin_bottom(18)
        self.edit_list_box_container.set_margin_start(18)
        self.edit_list_box_container.set_margin_end(18)
        self.edit_scrolled.set_child(self.edit_list_box_container)

        self.edit_page = self.view_stack.add_titled(self.edit_scrolled, "edit", tr("tab_edit"))
        self.edit_page.set_icon_name("document-edit-symbolic")

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        bottom_box.set_margin_start(12)
        bottom_box.set_margin_end(12)
        bottom_box.set_margin_bottom(12)

        apply_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        apply_row.set_halign(Gtk.Align.END)

        self.spinner = Gtk.Spinner()
        apply_row.append(self.spinner)

        self.apply_btn = Gtk.Button(label=tr("apply_btn_label"))
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.connect("clicked", self._on_apply_clicked)
        apply_row.append(self.apply_btn)

        bottom_box.append(apply_row)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(self.view_stack)
        main_box.append(Gtk.Separator())
        main_box.append(bottom_box)

        toolbar_view.set_content(main_box)
        self.toast_overlay.set_child(toolbar_view)
        self.set_content(self.toast_overlay)

        self.rows: list[ModuleRow] = []
        self.edit_rows: list[ModuleRow] = []
        self.category_rows: list[CategoryRow] = []
        self.reload()

        if self.config.load_warning:
            self.show_toast(self.config.load_warning)


    def _apply_theme(self, theme: str) -> None:
        style_manager = Adw.StyleManager.get_default()
        if theme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

    def _update_theme_button_icon(self) -> None:
        is_dark = Adw.StyleManager.get_default().get_dark()
        icon = "weather-clear-night-symbolic" if is_dark else "weather-clear-symbolic"
        self.theme_btn.set_icon_name(icon)

    def _on_theme_toggle_clicked(self, *_args) -> None:
        is_dark_now = Adw.StyleManager.get_default().get_dark()
        new_theme = "light" if is_dark_now else "dark"
        self.config.theme = new_theme
        self.config.save()
        self._apply_theme(new_theme)
        self._update_theme_button_icon()


    def _update_language_button_label(self) -> None:
        target = "EN" if self.translator.effective_language == "fr" else "FR"
        self.language_btn.set_label(target)

    def _on_language_toggle_clicked(self, *_args) -> None:
        new_language = "en" if self.translator.effective_language == "fr" else "fr"
        self.config.language = new_language
        self.config.save()
        self.translator.set_language(new_language)
        self._update_language_button_label()
        self._retranslate_static_widgets()
        self.reload()

    def _retranslate_static_widgets(self) -> None:
        tr = self.translator.tr
        self.set_title(tr("app_title"))
        self.categories_page.set_title(tr("tab_categories"))
        self.modules_page.set_title(tr("tab_modules"))
        self.edit_page.set_title(tr("tab_edit"))
        self.apply_btn.set_label(tr("apply_btn_label"))
        self.theme_btn.set_tooltip_text(tr("tooltip_theme"))
        self.language_btn.set_tooltip_text(tr("tooltip_language"))


    def _populate_container(
        self, container: Gtk.Box, edit_mode: bool
    ) -> list[ModuleRow]:
        tr = self.translator.tr
        for child in list(container):
            container.remove(child)

        rows: list[ModuleRow] = []

        if not self.config.modules:
            placeholder = Adw.StatusPage(
                title=tr("placeholder_no_modules_title"),
                description=tr("placeholder_no_modules_desc"),
                icon_name="folder-symbolic",
            )
            container.append(placeholder)
            return rows

        by_category: dict[str, list[ModuleEntry]] = {}
        for entry in self.config.modules:
            by_category.setdefault(entry.category, []).append(entry)

        for category in sorted(by_category.keys()):
            group = Adw.PreferencesGroup(title=category)
            list_box = Gtk.ListBox()
            list_box.set_selection_mode(Gtk.SelectionMode.NONE)
            list_box.add_css_class("boxed-list")

            for entry in by_category[category]:
                row = ModuleRow(entry, self, edit_mode=edit_mode)
                rows.append(row)
                list_box.append(row)

            group.add(list_box)
            container.append(group)

        return rows

    def _populate_categories(self, container: Gtk.Box) -> list[CategoryRow]:
        tr = self.translator.tr
        for child in list(container):
            container.remove(child)

        rows: list[CategoryRow] = []

        if not self.config.modules:
            placeholder = Adw.StatusPage(
                title=tr("placeholder_no_categories_title"),
                description=tr("placeholder_no_categories_desc"),
                icon_name="view-grid-symbolic",
            )
            container.append(placeholder)
            return rows

        by_category: dict[str, list[ModuleEntry]] = {}
        for entry in self.config.modules:
            by_category.setdefault(entry.category, []).append(entry)

        group = Adw.PreferencesGroup(description=tr("categories_group_desc"))
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")

        for category in sorted(by_category.keys()):
            row = CategoryRow(category, by_category[category], self)
            rows.append(row)
            list_box.append(row)

        group.add(list_box)
        container.append(group)

        return rows

    def reload(self) -> bool:
        self.rows = self._populate_container(self.list_box_container, edit_mode=False)
        self.edit_rows = self._populate_container(self.edit_list_box_container, edit_mode=True)
        self.category_rows = self._populate_categories(self.categories_list_box_container)
        return False

    def add_module(self, entry: ModuleEntry) -> None:
        tr = self.translator.tr
        self.config.modules.append(entry)
        self.config.save()
        GLib.idle_add(self.reload)
        self.show_toast(tr("toast_module_added", name=entry.name))

    def update_module(self, original: ModuleEntry, updated: ModuleEntry) -> None:
        tr = self.translator.tr
        try:
            idx = self.config.modules.index(original)
        except ValueError:
            self.show_toast(tr("toast_module_not_found"))
            return
        self.config.modules[idx] = updated
        self.config.save()
        GLib.idle_add(self.reload)
        self.show_toast(tr("toast_module_updated", name=updated.name))

    def remove_module(self, entry: ModuleEntry) -> None:
        tr = self.translator.tr
        try:
            self.config.modules.remove(entry)
        except ValueError:
            self.show_toast(tr("toast_module_already_deleted"))
            return
        self.config.save()
        GLib.idle_add(self.reload)
        self.show_toast(tr("toast_module_deleted", name=entry.name))

    def mark_dirty(self, name: str, new_state: bool) -> None:
        tr = self.translator.tr
        self._dirty = True
        state_key = "state_enabled" if new_state else "state_disabled"
        self.show_toast(tr("toast_module_toggled", name=name, state=tr(state_key)))

    def show_toast(self, message: str) -> None:
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))


    def _on_add_clicked(self, *_args) -> None:
        dialog = AddModuleDialog(self)
        dialog.present()

    def _on_prefs_clicked(self, *_args) -> None:
        dialog = PreferencesDialog(self)
        dialog.present()


    def _set_busy(self, busy: bool) -> None:
        self.scrolled.set_sensitive(not busy)
        self.edit_scrolled.set_sensitive(not busy)
        self.categories_scrolled.set_sensitive(not busy)
        self.apply_btn.set_sensitive(not busy)
        if busy:
            self.spinner.start()
            self.spinner.set_visible(True)
        else:
            self.spinner.stop()
            self.spinner.set_visible(False)

    def _on_apply_clicked(self, *_args) -> None:
        tr = self.translator.tr
        self._set_busy(True)
        self.show_toast(tr("toast_apply_opening"))

        rebuild_script = (
            "OLD_SYSTEM=$(readlink -f /run/current-system); "
            "pkexec nixos-rebuild switch --flake /etc/nixos#nixos; "
            "REBUILD_STATUS=$?; "
            "NEW_SYSTEM=$(readlink -f /run/current-system); "
            "if [ $REBUILD_STATUS -eq 0 ]; then "
            '  if [ "$OLD_SYSTEM" = "$NEW_SYSTEM" ]; then '
            '    echo; echo "Système déjà à jour, rien à changer."; '
            "  else "
            '    echo; echo "Mise à jour réussie. Différences :"; '
            '    nix store diff-closures "$OLD_SYSTEM" "$NEW_SYSTEM"; '
            "  fi; "
            "else "
            '  echo; echo "Échec du rebuild (code $REBUILD_STATUS)."; '
            "fi; "
            'echo; echo "Appuie sur Entrée pour fermer cette fenêtre."; '
            "read"
        )
        wrapped_cmd = ["bash", "-c", rebuild_script]
        terminal_commands = [
            ["kgx", "--"] + wrapped_cmd,
            ["gnome-terminal", "--"] + wrapped_cmd,
            ["konsole", "-e"] + wrapped_cmd,
            ["kitty"] + wrapped_cmd,
            ["alacritty", "-e"] + wrapped_cmd,
        ]

        self._try_spawn_terminal(terminal_commands, index=0)

    def _try_spawn_terminal(self, commands: list[list[str]], index: int) -> None:
        tr = self.translator.tr
        if index >= len(commands):
            self._set_busy(False)
            tried = ", ".join(c[0] for c in commands)
            self.show_toast(tr("toast_apply_no_terminal", tried=tried))
            return

        argv = commands[index]
        binary = argv[0]
        binary_path = shutil.which(binary)

        if binary_path is None:
            self._try_spawn_terminal(commands, index + 1)
            return

        try:
            subprocess.Popen(argv, start_new_session=True)
        except (OSError, FileNotFoundError) as exc:
            self.show_toast(tr("toast_apply_terminal_failed", binary=binary, error=str(exc)))
            self._try_spawn_terminal(commands, index + 1)
            return

        self._set_busy(False)
        self._dirty = False
        self.show_toast(tr("toast_apply_terminal_opened", binary=binary))


class TogglenixApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self) -> None:
        win = self.props.active_window
        if not win:
            win = MainWindow(self)
        win.present()


def main() -> int:
    app = TogglenixApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
