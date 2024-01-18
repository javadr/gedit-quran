VER=$(shell grep Version src/quran.plugin|cut -d= -f2)

all: version

version:
	@echo gedit-quran, Ver. $(VER)

install: version
	@echo "Installing..."
	@mkdir -p ~/.local/share/gedit/plugins/quran
	@cp -rfv src/quran.plugin $(HOME)/.local/share/gedit/plugins
	@cp -rfv src/quran/{{__init__,config}.py,quran.{metadata,txt.bz2,py,glade}} $(HOME)/.local/share/gedit/plugins/quran

uninstall: version
	@echo "Uninstalling..."
	@rm -rfv ~/.local/share/gedit/plugins/quran*

