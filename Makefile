TFM      := netstandard2.1
CONFIG   := Debug
DLL      := VGTTS.dll

BUILDDIR := VGTTS/bin/$(CONFIG)/$(TFM)
BUILDDLL := $(BUILDDIR)/$(DLL)

# WSL path to the game install — adjust if Steam lives elsewhere
GAME_DIR := /mnt/c/Program Files (x86)/Steam/steamapps/common/Vanguard Galaxy
PLUGIN_DIR := $(GAME_DIR)/BepInEx/plugins

# Resolve dotnet — prefer explicit local SDK, fall back to PATH
DOTNET   ?= $(shell command -v dotnet 2>/dev/null || echo /tmp/dnsdk/dotnet/dotnet)

BEPINEX_VERSION := 5.4.23.2
BEPINEX_URL     := https://github.com/BepInEx/BepInEx/releases/download/v$(BEPINEX_VERSION)/BepInEx_win_x64_$(BEPINEX_VERSION).zip

.PHONY: all build link-asm clean deploy deploy-bundle install-bepinex check-bepinex download-piper

all: build

# One-time: download and unpack BepInEx 5 into the game folder.
# Safe to re-run: overwrites loader files but leaves user plugins + config alone.
install-bepinex:
	@if [ -d "$(GAME_DIR)/BepInEx" ]; then \
		echo "BepInEx already installed at $(GAME_DIR)/BepInEx" ; \
	else \
		mkdir -p /tmp/bepinex-dl ; \
		curl -L -o /tmp/bepinex-dl/bepinex.zip "$(BEPINEX_URL)" ; \
		cd "$(GAME_DIR)" && unzip -o /tmp/bepinex-dl/bepinex.zip ; \
		echo "BepInEx installed. Launch the game once to initialize plugin folders." ; \
	fi

check-bepinex:
	@test -d "$(GAME_DIR)/BepInEx/plugins" || { \
		echo "BepInEx plugins dir not found at $(GAME_DIR)/BepInEx/plugins." ; \
		echo "Run 'make install-bepinex' then launch the game once." ; \
		exit 1 ; \
	}

# Symlink the game's Assembly-CSharp.dll into VGTTS/lib/ for compilation references.
link-asm:
	@mkdir -p VGTTS/lib
	@if [ ! -e "VGTTS/lib/Assembly-CSharp.dll" ]; then \
		ln -sf "$(GAME_DIR)/VanguardGalaxy_Data/Managed/Assembly-CSharp.dll" VGTTS/lib/Assembly-CSharp.dll ; \
		echo "Linked Assembly-CSharp.dll" ; \
	fi

build: link-asm
	DOTNET_ROOT=$(dir $(DOTNET)) $(DOTNET) build VGTTS/VGTTS.csproj -c $(CONFIG)

deploy: build check-bepinex
	@mkdir -p "$(PLUGIN_DIR)"
	cp "$(BUILDDLL)" "$(PLUGIN_DIR)/"
	@if [ -f "$(BUILDDIR)/VGTTS.pdb" ]; then cp "$(BUILDDIR)/VGTTS.pdb" "$(PLUGIN_DIR)/"; fi
	@echo "Deployed $(DLL) to $(PLUGIN_DIR)"
	@$(MAKE) deploy-bundle

# Deploy the Piper bundle (piper.exe + voice models) if present.
deploy-bundle:
	@if [ -d tools ]; then \
		mkdir -p "$(PLUGIN_DIR)/VGTTS" ; \
		cp -r tools "$(PLUGIN_DIR)/VGTTS/" ; \
		echo "Deployed tools bundle to $(PLUGIN_DIR)/VGTTS/tools" ; \
	else \
		echo "tools/ not found — skipping bundle deploy (run 'make download-piper')" ; \
	fi

PIPER_URL := https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip
VOICE_BASE := https://huggingface.co/rhasspy/piper-voices/resolve/main/en
VOICES := \
  en_US-amy-medium:en_US/amy/medium \
  en_US-ryan-medium:en_US/ryan/medium \
  en_GB-alan-medium:en_GB/alan/medium \
  en_US-hfc_female-medium:en_US/hfc_female/medium \
  en_US-kristin-medium:en_US/kristin/medium \
  en_GB-jenny_dioco-medium:en_GB/jenny_dioco/medium \
  en_US-lessac-high:en_US/lessac/high \
  en_US-ryan-high:en_US/ryan/high \
  en_US-libritts_r-medium:en_US/libritts_r/medium

download-piper:
	@mkdir -p tools/piper tools/voices /tmp/piper-dl
	@if [ ! -f tools/piper/piper.exe ]; then \
		echo "Downloading piper..." ; \
		curl -sSL -o /tmp/piper-dl/piper.zip "$(PIPER_URL)" ; \
		rm -rf /tmp/piper-dl/extracted && mkdir -p /tmp/piper-dl/extracted ; \
		unzip -q /tmp/piper-dl/piper.zip -d /tmp/piper-dl/extracted ; \
		cp -r /tmp/piper-dl/extracted/piper/* tools/piper/ ; \
	fi
	@for entry in $(VOICES); do \
		name=$${entry%%:*} ; path=$${entry##*:} ; \
		if [ ! -f "tools/voices/$$name.onnx" ]; then \
			echo "Downloading voice $$name..." ; \
			curl -sSL -o "tools/voices/$$name.onnx"      "$(VOICE_BASE)/$$path/$$name.onnx" ; \
			curl -sSL -o "tools/voices/$$name.onnx.json" "$(VOICE_BASE)/$$path/$$name.onnx.json" ; \
		fi ; \
	done
	@echo "Piper bundle ready in tools/"

clean:
	$(DOTNET) clean VGTTS/VGTTS.csproj
	rm -rf VGTTS/bin VGTTS/obj
