#!/usr/bin/env python3

import gi
import re
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
                "latex_command_checkbox", "ok_button", #"cancel_button",
                "surah_label_event_box",
                "from_ayah_event_box", "to_ayah_event_box",
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
        # region ComboBox for Sura #############################################
        # Set RTL text direction for the GtkCellRendererText
        cell_renderer = self.surah_combo.get_cells()[0]
        cell_renderer.set_property("xalign", 1.0)  # Align text to the right
        for i, (arabic, english) in enumerate(zip(self.quran.suras_ar, self.quran.suras_en), 1):
            self.surah_store.append([f"{i: 3}. {arabic} ({english})"])
        self.surah_combo.set_active(0)
        self.surah_combo.connect("changed", self.on_surah_name_changed)
        entry = self.surah_combo.get_child()
        entry.set_text(f"{self.config['surah']}")
        # endregion
        # region ComboBox for Aya ##############################################
        for i in range(1,8):
            self.from_ayah_store.append([f"{i}"])
        self.from_ayah_combo.set_active(0)
        for i in range(1,8):
            self.to_ayah_store.append([f"{i}"])
        self.to_ayah_combo.set_active(0)
        # Get the entry widget embedded in the combo box
        entry = self.from_ayah_combo.get_child()
        entry.set_text(f"{self.config['from_ayah']}")
        # Connect the "changed" signal of the entry to a callback
        entry.connect("key-press-event", self.on_key_press_ayah)
        entry.connect("changed", self.on_changed_ayah_combo, "from")
        entry.connect("activate", self.on_entry_activate, self.ok_button)
        entry = self.to_ayah_combo.get_child()
        entry.set_text(f"{self.config['to_ayah']}")
        entry.connect("key-press-event", self.on_key_press_ayah)
        entry.connect("changed", self.on_changed_ayah_combo, "to")
        entry.connect("activate", self.on_entry_activate, self.ok_button)
        # endregion ############################################################
        self.ok_button.connect("clicked", self.on_ok_button_clicked)

    def on_from_ayah_clicked(self, widget, event):
        to_entry = self.from_ayah_combo.get_child()
        to_entry.set_text("1")

    def on_to_ayah_clicked(self, widget, event):
        to_entry = self.to_ayah_combo.get_child()
        active_surah = self._get_active_iter_combo(self.surah_combo)
        surah_order = int(active_surah.split(".")[0])-1
        to_entry.set_text(f"{self.quran.suras_ayat[surah_order]}")

    def on_surah_label_clicked(self, widget, event):
        self.on_from_ayah_clicked(widget, event)
        self.on_to_ayah_clicked(widget, event)

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
        ayah_count = self.quran.suras_ayat[int(self._get_active_iter_combo(self.surah_combo).split(".")[0])-1]
        num = int(text)
        ayah = int(text) if num<=ayah_count else ayah_count
        entry.set_text(f"{ayah}")

        for combo in ("from_ayah", "to_ayah"):
            self.config[combo] = int(
                self._get_active_iter_combo(getattr(self, f"{combo}_combo"))
                )
        # Unblock the signal
        entry.handler_unblock_by_func(self.on_changed_ayah_combo)

    def _get_active_iter_combo(self, widget):
        entry = widget.get_child()
        return entry.get_text().strip()

    def on_surah_name_changed(self, widget):
        active_surah = self._get_active_iter_combo(widget)
        if active_surah is not None:
            surah_order = int(active_surah.split(".")[0])-1
            logger.debug(f"{active_surah} has total {self.quran.suras_ayat[surah_order]} of Ayat.")
            cell = Gtk.CellRendererText()
            self.from_ayah_combo.pack_start(cell, True)
            # self.from_ayah_combo.add_attribute(cell, "text", 0)
            self.from_ayah_store.clear()
            self.to_ayah_store.clear()
            for i in range(1,self.quran.suras_ayat[surah_order]+1):
                self.from_ayah_store.append([f"{i}"])
                self.to_ayah_store.append([f"{i}"])
            # self.from_ayah_combo.set_active(0)
            self.on_surah_label_clicked(widget, None)

            self.config["surah"] = active_surah

    def on_ok_button_clicked(self, widget):
        buffer = self.window.get_active_view().get_buffer()
        cursor_position = buffer.get_iter_at_mark(buffer.get_insert())

        cursor_position.backward_char()
        char_before_cursor = cursor_position.get_text(buffer.get_iter_at_mark(buffer.get_insert()))
        cursor_position.forward_char()

        # Handle OK button click
        # self.dialog.response(Gtk.ResponseType.ACCEPT)
        surah = int(self._get_active_iter_combo(self.surah_combo).split(".")[0])
        try:
            from_ayah = int(self._get_active_iter_combo(self.from_ayah_combo))
            to_ayah = int(self._get_active_iter_combo(self.to_ayah_combo))
            logger.debug(f"Typesetting Surah {self.quran.suras_en[surah]} from Ayah {from_ayah} to {to_ayah}.")
        except (ValueError, TypeError):
            return

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

        self.dialog.close()

    def on_quran_activate(self, action, parameter):
        if not self.dialog:
            self._create_dialog()

        self.dialog.show()

    def on_dialog_destroy(self, dialog):
        self.dialog = None
