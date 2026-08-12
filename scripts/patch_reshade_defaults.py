#!/usr/bin/env python3
"""
Le um preset .ini do ReShade e reescreve os valores default (initializer)
dos uniforms correspondentes nos arquivos .fx, ja que o vkbasalt nao tem
sistema de preset e usa apenas o valor hardcoded no shader.

Uso:
    python3 patch_reshade_defaults.py preset.ini /opt/rbgw-reshade/Shaders /opt/rbgw-reshade-patched/Shaders

Nao sobrescreve os .fx originais - grava em outdir. Sempre revise o diff
antes de apontar o vkBasalt.conf para os arquivos patcheados.
"""
import configparser
import re
import shutil
import sys
from pathlib import Path


_BOOL_RE = re.compile(r"^(true|false)$", re.IGNORECASE)
_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+(?:[eE][-+]?\d+)?$")
_VECTOR_RE = re.compile(r"^\s*(float\d)\s*\((.*)\)\s*$", re.DOTALL)


def format_value(raw_value: str, original_initializer: str):
    """Formata o valor do ini no mesmo TIPO do initializer original (bool/int/float/vetor).
    Retorna None se o initializer original nao for um literal numerico/bool reconhecivel
    (ex: identificador de enum/macro) - nesse caso o chamador deve pular a substituicao."""
    orig = original_initializer.strip()

    vec_match = _VECTOR_RE.match(orig)
    if vec_match:
        vec_type = vec_match.group(1)
        parts = [p.strip() for p in raw_value.split(",")]
        try:
            floats = ", ".join(f"{float(p):g}" if float(p) != int(float(p)) else f"{float(p):.1f}" for p in parts)
        except ValueError:
            return None
        return f"{vec_type}({floats})"

    raw = raw_value.strip()

    if _BOOL_RE.match(orig):
        try:
            truthy = raw.lower() in ("1", "true") or float(raw) != 0.0
        except ValueError:
            truthy = raw.lower() == "true"
        return "true" if truthy else "false"

    if _INT_RE.match(orig):
        try:
            return str(int(round(float(raw))))
        except ValueError:
            return None

    if _FLOAT_RE.match(orig) or orig.lower() in ("0", "1"):
        try:
            f = float(raw)
        except ValueError:
            return None
        return f"{f:g}" if f != int(f) else f"{f:.1f}"

    # initializer original nao e um literal reconhecido (provavel enum/macro, ex: DA_W)
    return None


def patch_fx_file(fx_path: Path, uniform_values: dict, out_path: Path) -> list:
    """Retorna lista de (uniform, valor_antigo, valor_novo) aplicados."""
    text = fx_path.read_text(encoding="utf-8", errors="ignore")
    changes = []

    for name, raw_value in uniform_values.items():
        # Casa: uniform <tipo> NAME [< ...anotacoes... >] = <initializer>;
        # Anotacoes podem conter { } < > aninhados de expressoes, entao usamos
        # um casamento nao-guloso ate o ';' final da declaracao.
        pattern = re.compile(
            r"(uniform\s+\w+\s+" + re.escape(name) + r"\s*(?:<.*?>\s*)?=\s*)([^;]+)(;)",
            re.DOTALL,
        )
        match = pattern.search(text)
        if not match:
            print(f"  [aviso] uniform '{name}' nao encontrado em {fx_path.name}, pulando")
            continue

        old_value = match.group(2).strip()
        new_value = format_value(raw_value, old_value)
        if new_value is None:
            print(f"  [aviso] '{name}': initializer original '{old_value}' nao e um literal numerico/bool "
                  f"reconhecido (provavel enum/macro) - NAO patcheado, mantido como estava")
            continue
        text = text[: match.start(2)] + new_value + text[match.end(2):]
        changes.append((name, old_value, new_value))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return changes


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    ini_path, shaders_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

    if not ini_path.is_file():
        print(f"[erro] arquivo .ini nao encontrado: {ini_path.resolve()}")
        sys.exit(1)
    if not shaders_dir.is_dir():
        print(f"[erro] diretorio de shaders nao encontrado: {shaders_dir.resolve()}")
        sys.exit(1)

    raw_text = ini_path.read_text(encoding="utf-8", errors="ignore")
    first_bracket = raw_text.find("[")
    if first_bracket == -1:
        print("[erro] nenhum cabecalho de secao '[...]' encontrado no .ini")
        sys.exit(1)
    # descarta linhas soltas (Techniques=..., TechniqueSorting=...) antes da 1a secao
    ini_body = raw_text[first_bracket:]

    cfg = configparser.ConfigParser(strict=False, delimiters=("=",))
    cfg.optionxform = str  # preserva maiusculas/minusculas dos nomes
    cfg.read_string(ini_body)

    fx_sections = [s for s in cfg.sections() if s.endswith(".fx")]
    if not fx_sections:
        print("[erro] nenhuma secao '[algo.fx]' encontrada apos o parse - confira o conteudo do .ini")
        sys.exit(1)
    print(f"Secoes .fx encontradas: {fx_sections}")

    for section in fx_sections:
        fx_name = section.split("@")[-1] if "@" in section else section
        fx_path = shaders_dir / fx_name
        if not fx_path.exists():
            print(f"[aviso] {fx_path} nao existe, pulando secao [{section}]")
            continue

        out_path = out_dir / fx_name
        values = dict(cfg.items(section))
        print(f"\n== {fx_name} ==")
        changes = patch_fx_file(fx_path, values, out_path)
        for name, old, new in changes:
            print(f"  {name}: {old} -> {new}")
        if not changes:
            shutil.copy(fx_path, out_path)

    print(f"\nArquivos patcheados em: {out_dir}")
    print("Revise com 'diff -u' contra os originais antes de usar no vkBasalt.conf.")


if __name__ == "__main__":
    main()
