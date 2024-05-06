#!/usr/bin/env python3

import gi
import os
import logging

from gi.repository import GObject, Gio, Gtk, Gdk, Gedit
from .quran import Quran, SOURCE_DIR
from .config import Config

gi.require_version("Gedit", "3.0")
gi.require_version("Gtk", "3.0")

logger = logging.getLogger("gedit-quran-plugin")
logger.addHandler(logging.StreamHandler())
if os.environ.get("GEDIT_QURAN_PLUGIN_DEBUG"):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.WARN)


class QuranAppActivatable(GObject.Object, Gedit.AppActivatable):
    app = GObject.Property(type=Gedit.App)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.app.add_accelerator("<Alt>q", "win.quran", None)

        self.menu_ext = self.extend_menu("tools-section")
        item = Gio.MenuItem.new("Quran…", "win.quran")
        self.menu_ext.prepend_menu_item(item)

    def do_deactivate(self):
        self.app.remove_accelerator("win.quran", None)



class QuranPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "QuranPlugin"
    quran = Quran()
    config = Config()

    window = GObject.Property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    @property
    def dialog_size(self):
        return self._dialog_size

    @dialog_size.setter
    def dialog_size(self, value):
        self._dialog_size = value

    def do_activate(self):
        self.dialog_size = (350, 100)
        self.dialog = None

        action = Gio.SimpleAction(name="quran")
        action.connect("activate", self.on_quran_activate)
        self.window.add_action(action)

    def do_deactivate(self):
        self.window.remove_action("quran")

    def _create_dialog(self):
        """Create dialog box."""
        builder = Gtk.Builder()
        builder.add_from_file(str(SOURCE_DIR/"quran.glade"))
        # builder.connect_signals(Handler(self))
        self.dialog = builder.get_object("quran_window")
        for item in (
                "surah_store", "from_ayah_store", "to_ayah_store",
                "surah_combo", "from_ayah_combo", "to_ayah_combo",
                "ayah_address_checkbox","newline_checkbox",
                "latex_command_checkbox", "tanzil_checkbox",
                "ok_button", #"cancel_button",
                "surah_label_event_box",
                "from_ayah_event_box", "to_ayah_event_box",
                "entry_completion",
            ):
            setattr(self, item, builder.get_object(item))

        # builder.connect_signals(Handler(self))
        self.window.get_group().add_window(self.dialog)

        self.dialog.set_title("Quran")
        self.dialog.set_default_size(*self.dialog_size)
        self.dialog.set_transient_for(self.window)
        self.dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.dialog.connect("destroy", self.on_dialog_destroy)
        self.dialog.connect("key-press-event", self.on_key_press)
        self.surah_label_event_box.connect("button-press-event", self.on_surah_label_clicked)
        self.from_ayah_event_box.connect("button-press-event", self.on_from_ayah_clicked)
        self.to_ayah_event_box.connect("button-press-event", self.on_to_ayah_clicked)
        ########################################################################
        # region ComboBox for Sura #############################################
        ## Set RTL text direction for the GtkCellRendererText
        cell_renderer = self.surah_combo.get_cells()[0]
        cell_renderer.set_property("xalign", 1.0)  # Align text to the right
        for i, (arabic, english) in enumerate(zip(self.quran.suras_ar, self.quran.suras_en), 1):
            self.surah_store.append([f"{i}. {arabic} ({english})"])
        self.surah_combo.connect_after("changed", self.on_surah_name_changed)
        entry = self.surah_combo.get_child()
        entry.set_text(f"{self.config['Quran']['surah']}")
        entry.select_region(0, -1)
        entry.connect("activate", self.on_entry_activate, self.ok_button)
        ## To make force the from/to_ayah updated in compliance with the surah
        self.on_surah_name_changed(self.surah_combo)
        self.entry_completion.set_match_func(self.match_func)
        # endregion ############################################################
        ########################################################################
        ## set active items of combo boxes
        surah_idx = int(self.config["Quran"]["surah"].split(".")[0])-1
        self.surah_combo.set_active(surah_idx)
        self.from_ayah_combo.set_active(int(self.config["Quran"]["from_ayah"])-1)
        self.to_ayah_combo.set_active(int(self.config["Quran"]["to_ayah"])-1)
        ########################################################################
        # region ComboBox for Aya ##############################################
        ## from_ayah combo button
        ## Get the entry widget embedded in the combo box
        entry = self.from_ayah_combo.get_child()
        entry.connect("key-press-event", self.on_key_press_ayah)
        entry.connect("changed", self.on_changed_ayah_combo, "from")
        entry.connect("activate", self.on_entry_activate, self.ok_button)
        entry.set_text(f"{self.config['Quran']['from_ayah']}")
        ## to_ayah combo button
        entry = self.to_ayah_combo.get_child()
        entry.set_text(f"{self.config['Quran']['to_ayah']}")
        entry.connect("key-press-event", self.on_key_press_ayah)
        entry.connect("changed", self.on_changed_ayah_combo, "to")
        entry.connect("activate", self.on_entry_activate, self.ok_button)
        # endregion ############################################################
        ########################################################################
        # region Settings' loading + signals' connectins #######################
        for item in ("ayah_address", "newline", "latex_command", "tanzil"):
            check_button = getattr(self, f"{item}_checkbox")
            check_button.set_active(self.config["Settings"].getboolean(item))
            ## Connect the button's "toggled" signal to a callback
            check_button.connect("toggled", self.on_check_button_toggled, item)
        # endregion ############################################################
        ########################################################################
        self.ok_button.connect("clicked", self.on_ok_button_clicked)

    def match_func(self, completion, key, iter, data=None):
        model = completion.get_model()
        text = model[iter][0].lower()
        key = key.lower()
        return key in text

    def on_check_button_toggled(self, check_button, item):
        self.config["Settings"] = { item: check_button.get_active() }

    def on_from_ayah_clicked(self, widget, event):
        to_entry = self.from_ayah_combo.get_child()
        to_entry.set_text("1")

    def on_to_ayah_clicked(self, widget, event):
        to_entry = self.to_ayah_combo.get_child()
        active_surah = self._get_active_iter_combo(self.surah_combo)
        surah_order = int(active_surah.split(".")[0])-1
        to_entry.set_text(f"{self.quran.suras_ayat[surah_order]}")

    def on_surah_label_clicked(self, widget, event):
        surah, ayah = self.quran.random_verse()
        entry = self.surah_combo.get_child()
        entry.set_text(f"{surah}. {self.quran.suras_ar[surah-1]} ({self.quran.suras_en[surah-1]})")
        entry = self.from_ayah_combo.get_child()
        entry.set_text(f"{ayah}")
        entry = self.to_ayah_combo.get_child()
        entry.set_text(f"{ayah}")

    def on_entry_activate(self, entry, button):
        # This function is called when Enter key is pressed in the entry
        # Trigger the button's clicked event
        button.clicked()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.dialog.destroy()

    def on_key_press_ayah(self, widget, event):
        # Get the key value from the event
        keyval = event.keyval
        # Filter out non-digit key presses
        if Gdk.keyval_name(keyval).isalpha() and keyval in (list(range(58,256))+[32]):
            # Return True to stop further handling by other signal handlers
            return True

    def on_changed_ayah_combo(self, entry, from_or_to="from"):
        # Get the current text content inside the entry
        text = entry.get_text()
        if not text:
            return
        # Block the signal temporarily to avoid recursion
        entry.handler_block_by_func(self.on_changed_ayah_combo)
        ayah_count = self.quran.suras_ayat[
            int(self._get_active_iter_combo(self.surah_combo).split(".")[0])-1
            ]
        num = int(text)
        ayah = int(text) if num<=ayah_count else ayah_count
        entry.set_text(f"{ayah}")

        for combo in ("from_ayah", "to_ayah"):
            self.config["Quran"] = {
                combo : int(self._get_active_iter_combo(getattr(self, f"{combo}_combo"))),
            }

        # Unblock the signal
        entry.handler_unblock_by_func(self.on_changed_ayah_combo)

    def _get_active_iter_combo(self, widget):
        entry = widget.get_child()
        return entry.get_text().strip()

    def on_surah_name_changed(self, widget):
        active_surah = self._get_active_iter_combo(widget)
        if active_surah is not None:
            try:
                surah_order = int(active_surah.split(".")[0])-1
            except ValueError:
                return
            logger.debug(f"{active_surah} has total {self.quran.suras_ayat[surah_order]} of Ayat.")
            cell = Gtk.CellRendererText()
            self.from_ayah_combo.pack_start(cell, True)
            self.from_ayah_store.clear()
            self.to_ayah_store.clear()
            for i in range(1,self.quran.suras_ayat[surah_order]+1):
                self.from_ayah_store.append([f"{i}"])
                self.to_ayah_store.append([f"{i}"])
            self.on_from_ayah_clicked(widget, None)
            self.on_to_ayah_clicked(widget, None)
            self.config["Quran"] = dict(surah=active_surah)

    def on_ok_button_clicked(self, widget):
        try:
            buffer = self.window.get_active_view().get_buffer()
            cursor_position = buffer.get_iter_at_mark(buffer.get_insert())

            cursor_position.backward_char()
            char_before_cursor = cursor_position.get_text(buffer.get_iter_at_mark(buffer.get_insert()))
            cursor_position.forward_char()
        except (AttributeError, ):
            buffer = None
        # Handle OK button click
        # self.dialog.response(Gtk.ResponseType.ACCEPT)
        try:
            surah = int(self._get_active_iter_combo(self.surah_combo).split(".")[0])
            from_ayah = int(self._get_active_iter_combo(self.from_ayah_combo))
            to_ayah = int(self._get_active_iter_combo(self.to_ayah_combo))
            if from_ayah > to_ayah:
                return
            logger.debug(f"Typesetting Surah {self.quran.suras_en[surah-1]}"
                         f"from Ayah {from_ayah} to {to_ayah}.")
        except (ValueError, TypeError):
            return

        # If there is an open windown, typesets it
        if buffer is not None:
            sep = "\n" if self.newline_checkbox.get_active() else " "
            pre = " " if cursor_position.get_line_offset() and char_before_cursor!=" " else ""
            if self.latex_command_checkbox.get_active():
                output = self.quran.latex(surah, from_ayah, to_ayah)
            else:
                Ayat = self.quran.get_verse(surah, from_ayah, to_ayah)
                output = sep.join(
                    [
                    ayah
                    + f" ﴿{self.quran.suras_ar[surah-1] if from_ayah==to_ayah else ''}{num}﴾"
                    if self.ayah_address_checkbox.get_active() else ""
                    for (ayah, num) in Ayat
                    ],
                )
            output = f"{pre}{output}{sep}"
            buffer.insert(cursor_position, output)

        if self.tanzil_checkbox.get_active():
            # Open the URL in the default web browser
            Gtk.show_uri(None, f"https://tanzil.net/#{surah}:{from_ayah}", 0)

        self.dialog.close()

    def on_quran_activate(self, action, parameter):
        if not self.dialog:
            self._create_dialog()

        self.dialog.show()

    def on_dialog_destroy(self, dialog):
        self.dialog = None
