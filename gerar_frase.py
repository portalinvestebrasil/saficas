#!/usr/bin/env python3
"""Motor de frase safica: le pautas_saficas.json, escolhe uma pauta e chama o Claude."""
import os, sys, json, random, argparse
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
PAUTAS_FILE = BASE / "pautas_saficas.json"
STATE_FILE = BASE / ".estado_motor.json"
MODEL = "claude-haiku-4-5-20251001"

def carregar_banco():
    return json.loads(PAUTAS_FILE.read_text(encoding="utf-8"))

def ler_estado():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"ultimo_id": None}

def salvar_estado(pauta_id):
    STATE_FILE.write_text(json.dumps({"ultimo_id": pauta_id}), encoding="utf-8")

def escolher_modo(forcar=None):
    if forcar:
        return forcar
    h = datetime.now().hour
    return "noite" if (h >= 19 or h < 5) else "dia"

def escolher_pauta(banco, modo, ultimo_id):
    pautas = [p for p in banco["pautas"] if modo in p["modos"]]
    if len(pautas) > 1 and ultimo_id:
        pautas = [p for p in pautas if p["id"] != ultimo_id] or pautas
    pesos = [p.get("peso", 1) for p in pautas]
    return random.choices(pautas, weights=pesos, k=1)[0]

def montar_prompt(config, pauta, modo):
    voz = "\n".join("- " + r for r in config["regras_voz"])
    proib = "\n".join("- " + r for r in config["proibido"])
    cta = "\n".join(str(i+1) + ". " + s for i, s in enumerate(config["regras_legenda"]["estrutura"]))
    lim = config["limites"]
    tom = "luminoso, declaracao aberta e calorosa" if modo == "dia" else "confissao em voz baixa, sensorial e corporal, intima mas NUNCA sexual"
    system = (
        "Voce escreve frases romanticas curtas para um perfil de Instagram sobre amor entre duas mulheres (" + config["handle"] + ").\n\n"
        "REGISTRO: " + config["registro"] + "\n\n"
        "REGRAS DE VOZ (siga todas):\n" + voz + "\n\n"
        "PROIBIDO (nunca faca):\n" + proib + "\n\n"
        "MODO DESTE POST: " + modo + " - tom " + tom + ".\n\n"
        "FORMATO DA FRASE:\n"
        "- No maximo " + str(lim["frase_max_linhas"]) + " linhas, ~" + str(lim["frase_chars_por_linha"]) + " caracteres por linha.\n"
        "- Use quebras de linha onde a frase respira. " + lim["regra"] + ".\n"
        "- E uma frase NOVA e original. A frase_norte da pauta e so uma bussola - NUNCA copie.\n\n"
        "ESTRUTURA DA LEGENDA:\n" + cta + "\nMais hashtags: " + config["regras_legenda"]["hashtags"] + ".\n\n"
        "Responda SOMENTE com JSON valido, sem markdown:\n"
        '{"frase": "linha1\\nlinha2", "legenda": "texto", "hashtags": ["#a", "#b"]}'
    )
    user = (
        "Gere o post agora.\n"
        "Pauta: " + pauta["nome"] + " - " + pauta["tema"] + ".\n"
        "Botao emocional: " + pauta["gancho_emocional"] + ".\n"
        "Bussola (NAO copiar): " + pauta["frase_norte"] + "\n"
        "Modo: " + modo + "."
    )
    return system, user

def gerar(system, user):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=1000, system=system,
        messages=[{"role": "user", "content": user}],
    )
    txt = "".join(b.text for b in msg.content if b.type == "text").strip()
    txt = txt.replace("```json", "").replace("```", "").strip()
    return json.loads(txt)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--modo", choices=["dia", "noite"])
    args = ap.parse_args()
    banco = carregar_banco()
    estado = ler_estado()
    modo = escolher_modo(args.modo)
    pauta = escolher_pauta(banco, modo, estado["ultimo_id"])
    system, user = montar_prompt(banco["config"], pauta, modo)
    if args.dry_run:
        print("=== MODO:", modo, "| PAUTA:", pauta["id"], pauta["nome"], "===\n")
        print("----- SYSTEM -----\n" + system)
        print("\n----- USER -----\n" + user)
        return
    out = gerar(system, user)
    out["modo"] = modo
    out["pauta_id"] = pauta["id"]
    salvar_estado(pauta["id"])
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
