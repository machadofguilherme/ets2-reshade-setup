#!/usr/bin/env bash
# Automatiza a instalacao manual do ReShade no ETS2 (ou outro jogo D3D11/DXGI
# via Proton): extrai a dxgi.dll do instalador, monta os symlinks de shaders,
# copia o preset e baixa os headers .fxh que faltam.
#
# Uso:
#   ./install-reshade.sh <ReShade_Setup_X.X.X.exe> <pasta_do_jogo/bin/win_x64> \
#       <pasta_com_Shaders_e_Textures> <preset.ini>
#
# Requer: 7z (p7zip), wget, unzip
set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "Uso: $0 <ReShade_Setup.exe> <pasta_bin_do_jogo> <pasta_shaders_textures> <preset.ini>"
    exit 1
fi

INSTALLER="$1"
GAME_BIN_DIR="$2"
SHADERS_ROOT="$3"   # deve conter Shaders/ e Textures/
PRESET_INI="$4"

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "==> Extraindo o instalador do ReShade..."
7z x "$INSTALLER" -o"$WORKDIR/extracted" > /dev/null

DLL=$(find "$WORKDIR/extracted" -iname "ReShade64.dll" | head -n1)
if [ -z "$DLL" ]; then
    echo "[erro] ReShade64.dll nao encontrado dentro do instalador extraido"
    exit 1
fi
echo "    Encontrado: $DLL"

echo "==> Copiando como dxgi.dll para $GAME_BIN_DIR"
cp "$DLL" "$GAME_BIN_DIR/dxgi.dll"

echo "==> Montando estrutura reshade-shaders/ via symlink"
mkdir -p "$GAME_BIN_DIR/reshade-shaders"
ln -sf "$SHADERS_ROOT/Shaders" "$GAME_BIN_DIR/reshade-shaders/Shaders"
ln -sf "$SHADERS_ROOT/Textures" "$GAME_BIN_DIR/reshade-shaders/Textures"

echo "==> Copiando preset"
cp "$PRESET_INI" "$GAME_BIN_DIR/"

echo "==> Baixando headers .fxh que faltam (ReShade.fxh, ReShadeUI.fxh, SMAA.fxh)"
cd "$SHADERS_ROOT/Shaders"
[ -f ReShade.fxh ] || wget -q https://raw.githubusercontent.com/crosire/reshade-shaders/slim/Shaders/ReShade.fxh
[ -f ReShadeUI.fxh ] || wget -q https://raw.githubusercontent.com/crosire/reshade-shaders/slim/Shaders/ReShadeUI.fxh

if [ ! -f SMAA.fxh ]; then
    echo "    Baixando SweetFX (fonte do SMAA.fxh)..."
    wget -q https://github.com/CeeJayDK/SweetFX/archive/refs/heads/master.zip -O "$WORKDIR/sweetfx.zip"
    unzip -j "$WORKDIR/sweetfx.zip" "SweetFX-master/Shaders/SweetFX/SMAA.fxh" -d "$SHADERS_ROOT/Shaders" > /dev/null
fi

echo "==> Pronto."
echo ""
echo "Falta so:"
echo "  1. Abrir o jogo, apertar Home, configurar em Settings:"
echo "     Effect search paths:  .\\reshade-shaders\\Shaders\\**"
echo "     Texture search paths: .\\reshade-shaders\\Textures\\**"
echo "  2. Fechar e abrir o jogo de novo (forca reload dos paths)"
echo "  3. Carregar o preset $(basename "$PRESET_INI") na aba Home"
echo ""
echo "Se algum efeito falhar ao compilar com erro tipo 'not yet implemented"
echo "feature', roda: protontricks <APPID> d3dcompiler_47"
