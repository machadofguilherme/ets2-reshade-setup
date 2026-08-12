# ReShade (RBGW SMAA + TAA preset) no ETS2 via Proton

Documentação de como aplicar o preset `RBGW SMAA + TAA Preset.ini` no Euro
Truck Simulator 2 rodando via Proton no Linux. Escrito depois de uma sessão
de troubleshooting no Guix System (Steam via Flatpak); a intenção é que isso
sirva de referência rápida ao reinstalar em outra distro (ex: Gentoo, com
Steam nativa).

## Status no Guix (Flatpak Steam)

8 de 9 efeitos funcionando. `Clarity.fx` falha ao compilar por causa de uma
limitação de ambiente (ver seção "Problema conhecido: Clarity.fx" abaixo) —
não resolvido no Guix por causa da falta de multilib 32-bit; deve resolver
trivialmente numa distro com Steam nativa (ver seção "No Gentoo").

## Por que ReShade manual, e não vkBasalt

A primeira tentativa foi usar o **vkBasalt** (implicit Vulkan layer),
já que "não existe ReShade pra Linux". Isso funciona bem quando o jogo roda
nativamente. Mas com **Steam via Flatpak + Proton**, a cadeia de containers
aninhados (Flatpak sandbox → Steam Linux Runtime/pressure-vessel → Proton/
Wine → DXVK) impede o `winevulkan` de enumerar implicit layers do host —
mesmo com a extensão Flatpak correta instalada, `ENABLE_VKBASALT=1` presente
no ambiente do processo, e `VK_INSTANCE_LAYERS` forçado explicitamente.
Não é peculiaridade do Guix: há relatos do mesmo problema em outras distros
com Steam Flatpak + Proton.

**Decisão**: como o jogo já roda a build Windows via Proton (não a nativa
Linux, por causa de desempenho, mods de DLL e ProMods), o caminho certo é o
**ReShade de verdade** — ele injeta via DLL proxy (`dxgi.dll`), mecanismo
padrão do Windows que o Wine já suporta bem, sem depender de layer Vulkan
nenhuma. Reaproveitamos os `.fx`/Shaders/Textures que já tínhamos baixado.

O `vkBasalt.conf` que tínhamos montado ficou em `config/vkBasalt.conf.bak`
só de referência, caso um dia vkbasalt+Proton+Flatpak melhore.

## Passo a passo (instalação manual do ReShade)

Pressupõe que você já tem os Shaders/Textures do preset RBGW em algum lugar
(no caso original: `/opt/rbgw-reshade/Shaders` e `/opt/rbgw-reshade/Textures`)
e o `.ini` do preset.

### 1. Extrair a DLL do instalador do ReShade

O instalador (`ReShade_Setup_X.X.X.exe`, baixado em https://reshade.me) não
é Inno Setup — `innoextract` não funciona. Usa `7z`:

```bash
7z x ReShade_Setup_6.8.0.exe -oreshade_extracted
find reshade_extracted -iname "ReShade64.dll"
```

### 2. Copiar e renomear a DLL

Descobre a API gráfica do jogo primeiro (D3D9/D3D11/D3D12/OpenGL) — pro ETS2
via Proton confirmamos D3D11 (DXGI). Copia a DLL certa pra pasta do executável
e renomeia:

```bash
cp reshade_extracted/.../ReShade64.dll \
  "<pasta do jogo>/bin/win_x64/dxgi.dll"
```

Tabela de nomes por API (referência):
| API | Nome do arquivo |
|---|---|
| D3D9 | `d3d9.dll` |
| D3D10/11/12 | `dxgi.dll` (recomendado) |
| OpenGL | `opengl32.dll` |

### 3. Estrutura de shaders via symlink

O ReShade procura por padrão em `reshade-shaders/Shaders` e
`reshade-shaders/Textures`, relativos à DLL:

```bash
cd "<pasta do jogo>/bin/win_x64"
mkdir reshade-shaders
ln -s /opt/rbgw-reshade/Shaders reshade-shaders/Shaders
ln -s /opt/rbgw-reshade/Textures reshade-shaders/Textures
```

Symlinks Unix comuns funcionam bem — o Wine segue links do filesystem host
sem problema (diferente de atalhos `.lnk` do Windows).

### 4. Copiar o preset original

```bash
cp "RBGW SMAA + TAA Preset.ini" "<pasta do jogo>/bin/win_x64/"
```

Usa o `.ini` **original**, não patcheado — o ReShade de verdade tem sistema
de preset nativo, diferente do vkBasalt.

### 5. Headers que faltam (dependências dos .fx)

Shaders de terceiros dependem de headers-base que **não vêm** no pacote de
shaders específico (só vêm na instalação completa oficial). Erro típico no
log (`ReShade.log`, gerado do lado da dxgi.dll):

```
preprocessor error: could not open included file 'ReShadeUI.fxh'
preprocessor error: could not open included file 'ReShade.fxh'
preprocessor error: could not open included file 'SMAA.fxh'
```

Origem de cada um:
- `ReShade.fxh`, `ReShadeUI.fxh` → repositório oficial `crosire/reshade-shaders`,
  branch `slim`.
- `SMAA.fxh` (e o `SMAA.fx`/`Curves.fx`/`DPX.fx`/`Levels.fx`/`LumaSharpen.fx`
  do preset RBGW são originalmente da coleção **SweetFX**, não do repo
  principal) → `CeeJayDK/SweetFX`.

```bash
cd /opt/rbgw-reshade/Shaders
wget https://raw.githubusercontent.com/crosire/reshade-shaders/slim/Shaders/ReShade.fxh
wget https://raw.githubusercontent.com/crosire/reshade-shaders/slim/Shaders/ReShadeUI.fxh

# SMAA.fxh nao esta no repo "slim" - vem do SweetFX
cd /tmp
wget https://github.com/CeeJayDK/SweetFX/archive/refs/heads/master.zip -O sweetfx.zip
unzip -j sweetfx.zip "SweetFX-master/Shaders/SweetFX/*.fxh" -d /tmp/sweetfx-fxh
cp /tmp/sweetfx-fxh/SMAA.fxh /opt/rbgw-reshade/Shaders/
```

### 6. Configurar os search paths no overlay

Instalação manual não preenche o `ReShade.ini` automaticamente. Dentro do
jogo, aperta **Home**, vai em **Settings**, e configura:

- Effect search paths: `.\reshade-shaders\Shaders\**`
- Texture search paths: `.\reshade-shaders\Textures\**`

Fecha e abre o jogo de novo pra forçar reload (mais confiável que procurar
botão de reload na UI).

### 7. Carregar o preset

Na aba **Home** do overlay, seleciona o `.ini` copiado no passo 4.

## Problema conhecido: Clarity.fx

Erro de compilação:
```
E5017: Aborting due to not yet implemented feature: Unhandled attribute 'fastopt'
```

**Causa raiz**: a partir do ReShade 6.5+, o compilador tenta carregar o
`D3DCompiler_47.dll` real (Microsoft) do sistema. Sob Wine, esse
`LoadLibrary` é bloqueado ("Ignoring LoadLibrary('D3DCompiler_47.dll') call
to avoid possible deadlock" — visível no `ReShade.log`). Sem o compilador
real, o ReShade cai pro parser FX interno dele mesmo, que não implementa
certos padrões de sintaxe legada usados em shaders antigos (`Clarity.fx` é
de ~2017/2018). Os outros 8 efeitos do preset são simples o bastante pra não
bater nessa limitação.

**Fix**: instalar o `d3dcompiler_47.dll` real no prefix do Proton via
winetricks/protontricks.

### No Gentoo (Steam nativa)

Deve ser trivial:

```bash
protontricks 227300 d3dcompiler_47
```

(appid 227300 = Euro Truck Simulator 2). Precisa ter aberto o jogo pelo
menos uma vez antes, pro protontricks achar o `compatdata`.

### No Guix (ficou pendente)

Tentamos via `guix shell --container --emulate-fhs`, chegamos a rodar o
winetricks mas travou em `/lib/ld-linux.so.2: could not open` — falta
suporte a linker de 32-bit (Guix não tem multilib x86 maduro tipo
Debian/Ubuntu). Próxima tentativa não explorada: rodar o winetricks de
dentro do próprio Steam Linux Runtime (que já tem libs de 32 e 64 bits
funcionando, comprovado pelo jogo rodando):

```bash
"<Steam>/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point" --verb=run -- bash
# dentro desse shell:
env WINEPREFIX="<compatdata>/pfx" WINE="<Proton>/files/bin/wine" winetricks d3dcompiler_47
```

## Scripts auxiliares

- `scripts/patch_reshade_defaults.py`: usado durante a tentativa com vkBasalt
  pra reescrever os valores default hardcoded nos `.fx` a partir do `.ini`
  (necessário porque vkBasalt não tem sistema de preset). **Não é necessário
  pro fluxo final com ReShade real** — deixado aqui só de referência, caso
  precise gerar variantes fixas de algum shader no futuro.
