import gi
gi.require_version("Gedit", "3.0")
gi.require_version("Gtk", "3.0")
import re


from gi.repository import GObject, Gio, Gtk, Gedit
from .quran import Quran, SOURCE_DIR
try:
    import gettext
    gettext.bindtextdomain("gedit")
    gettext.textdomain("gedit")
    _ = gettext.gettext
except:
    _ = lambda s: s


class QuranAppActivatable(GObject.Object, Gedit.AppActivatable):
    app = GObject.Property(type=Gedit.App)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.app.add_accelerator("<Alt>q", "win.quran", None)

        self.menu_ext = self.extend_menu("tools-section")
        item = Gio.MenuItem.new(_("Quran…"), "win.quran")
        self.menu_ext.prepend_menu_item(item)

    def do_deactivate(self):
        self.app.remove_accelerator("win.quran", None)



class QuranPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "QuranPlugin"

    window = GObject.Property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self.quran = Quran()

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
        doc = self.window.get_active_document()

        builder = Gtk.Builder()
        builder.add_from_file(str(SOURCE_DIR/"quran.glade"))
        # builder.connect_signals(Handler(self))
        self.dialog = builder.get_object("quran_window")
        self.surah_combo = builder.get_object("surah_combo")
        self.surah_store = builder.get_object("surah_store")
        self.from_ayah_combo = builder.get_object("from_ayah_combo")
        self.to_ayah_combo = builder.get_object("to_ayah_combo")
        self.from_ayah_store = builder.get_object("from_ayah_store")
        self.to_ayah_store = builder.get_object("to_ayah_store")
        self.ok_button = builder.get_object("ok_button")
        self.cancel_button = builder.get_object("cancel_button")
        self.ayah_address_checkbox = builder.get_object("ayah_address_checkbox")
        self.newline_checkbox = builder.get_object("newline_checkbox")

        # builder.connect_signals(Handler(self))
        self.window.get_group().add_window(self.dialog)

        self.dialog.set_title("Quran")
        self.dialog.set_default_size(*self.dialog_size)
        self.dialog.set_transient_for(self.window)
        self.dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.dialog.connect("destroy", self.on_dialog_destroy)

        # region ComboBox for Sura #############################################
        # Set RTL text direction for the GtkCellRendererText
        cell_renderer = self.surah_combo.get_cells()[0]
        cell_renderer.set_property("xalign", 1.0)  # Align text to the right
        for i, (arabic, english) in enumerate(zip(self.quran.suras_ar, self.quran.suras_en), 1):
            self.surah_store.append([f"{i: 3}. {arabic} ({english})"])
        self.surah_combo.set_active(0)
        self.surah_combo.connect("changed", self.on_surah_name_changed)
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
        # Connect the "changed" signal of the entry to a callback
        entry.connect("changed", self.on_changed_ayah_combo)
        entry.connect("activate", self.on_entry_activate, self.ok_button)
        entry = self.to_ayah_combo.get_child()
        # Connect the "changed" signal of the entry to a callback
        entry.connect("activate", self.on_entry_activate, self.ok_button)

        # endregion ############################################################
        self.ok_button.connect("clicked", self.on_ok_button_clicked)
        self.cancel_button.connect("clicked", lambda x: self.dialog.close())

        # self.ok_button.grab_focus()

    def on_entry_activate(self, entry, button):
        # This function is called when Enter key is pressed in the entry
        # Trigger the button's clicked event
        button.clicked()

    def on_changed_ayah_combo(self, entry):
        # Get the current text content inside the entry
        text_content = entry.get_text()
        digit_only = re.sub(r"\D", "", text_content)
        # Block the signal temporarily to avoid recursion
        entry.handler_block_by_func(self.on_changed_ayah_combo)
        ayah = self.quran.suras_ayat[int(self._get_active_iter_combo(self.surah_combo).split(".")[0])-1]
        num = 0 if digit_only=="" else int(digit_only)
        from_ayah = digit_only if num<=ayah else ayah
        entry.set_text(f"{from_ayah}")
        to_ayah = int(self._get_active_iter_combo(self.to_ayah_combo))
        if num > to_ayah:
            to_entry = self.to_ayah_combo.get_child()
            to_entry.set_text(f"{from_ayah}")
        # Unblock the signal
        entry.handler_unblock_by_func(self.on_changed_ayah_combo)

    def _get_active_iter_combo(self, widget):
        entry = widget.get_child()
        return entry.get_text()
        # active_iter = widget.get_active_iter()
        # if active_iter is not None:
        #     model = widget.get_model()
        #     active_text = model[active_iter][0]
        #     return active_text

    def on_surah_name_changed(self, widget):
        active_surah = self._get_active_iter_combo(widget)
        if active_surah is not None:
            surah_order = int(active_surah.split(".")[0])-1
            print(f"{active_surah} has total {self.quran.suras_ayat[surah_order]} of Ayat.")
            cell = Gtk.CellRendererText()
            self.from_ayah_combo.pack_start(cell, True)
            # self.from_ayah_combo.add_attribute(cell, "text", 0)
            self.from_ayah_store.clear()
            for i in range(1,self.quran.suras_ayat[surah_order]+1):
                self.from_ayah_store.append([f"{i}"])
            self.from_ayah_combo.set_active(0)


    def on_ok_button_clicked(self, widget):
        buffer = self.window.get_active_view().get_buffer()
        cursor_position = buffer.get_iter_at_mark(buffer.get_insert())

        cursor_position.backward_char()
        char_before_cursor = cursor_position.get_text(buffer.get_iter_at_mark(buffer.get_insert()))
        cursor_position.forward_char()

        # Handle OK button click
        self.dialog.response(Gtk.ResponseType.ACCEPT)
        surah = int(self._get_active_iter_combo(self.surah_combo).split(".")[0])
        try:
            from_ayah = int(self._get_active_iter_combo(self.from_ayah_combo))
            to_ayah = int(self._get_active_iter_combo(self.to_ayah_combo))
        except (ValueError, TypeError):
            return
        sep = "\n" if self.newline_checkbox.get_active() else " "
        verse = sep.join(
            [
            self.quran.get_verse(surah, ayah).split("|")[-1]
            + f" ﴿{self.quran.suras_ar[surah-1] if from_ayah==to_ayah else ''}{ayah}﴾"
            if self.ayah_address_checkbox.get_active() else ""
            for ayah in range(from_ayah, to_ayah+1)
            ]
        )
        # if self.ayah_address_checkbox.get_active():
        #     verse += f" ﴿{self.quran.suras_ar[surah-1]} {ayah}﴾"
        pre = " " if cursor_position.get_line_offset() and char_before_cursor!=" " else ""
        verse = f"{pre}{verse}{sep}"
        buffer.insert(cursor_position, verse)

        self.dialog.close()

    def on_quran_activate(self, action, parameter, user_data=None):
        if not self.dialog:
            self._create_dialog()

        self.dialog.show()

    def on_dialog_destroy(self, dialog, user_data=None):
        # self.popup_size = popup._size
        self.dialog = None

#     def on_activated(self, gfile, user_data=None):
#         Gedit.commands_load_location(self.window, gfile, None, -1, -1)
#         return True