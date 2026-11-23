"""Tira as chaves do Supabase do YAML do job (gerado pelo `databricks bundle generate job`)
e guarda os valores em .databricks/bundle/dev/variable-overrides.json, que fica fora do Git.

Rode na pasta do bundle:  python scripts/tirar_chaves.py
"""
import json
import pathlib
import re

# 1 · acha o arquivo do job que o generate criou em resources/
arqs = list(pathlib.Path("resources").glob("*.job.yml"))
assert len(arqs) == 1, f"esperava 1 arquivo .job.yml em resources/, achei {arqs}. Rode na pasta do bundle."
arquivo = arqs[0]
yml = arquivo.read_text(encoding="utf-8")

# 2 · nome da variável no bundle  ->  nome do parâmetro no job
chaves = {"s3_access_key_id": "AWS_ACCESS_KEY_ID", "s3_secret_access_key": "AWS_SECRET_ACCESS_KEY"}

valores = {}
for var, param in chaves.items():
    achou = re.search(rf"{param}: (.+)", yml)
    assert achou, f"não achei {param} em {arquivo}: me mostre o arquivo SEM os valores das chaves"
    valor = achou.group(1).strip().strip("\"'")
    assert not valor.startswith("${var."), f"{param} já está como variável: o script já rodou antes"
    valores[var] = valor
    yml = re.sub(rf"{param}: .+", f"{param}: ${{var.{var}}}", yml)   # troca o valor pela variável

# 3 · declara as variáveis no topo do YAML
yml = "variables:\n" + "".join(
    f"  {v}:\n    description: chave do data lake (o valor fica fora do Git)\n" for v in chaves
) + "\n" + yml
arquivo.write_text(yml, encoding="utf-8")

# 4 · os valores vão para a pasta .databricks/, que o .gitignore deixa fora do Git
pasta = pathlib.Path(".databricks/bundle/dev")
pasta.mkdir(parents=True, exist_ok=True)
(pasta / "variable-overrides.json").write_text(json.dumps(valores), encoding="utf-8")

print("ok: as chaves saíram de", arquivo, "e foram para", pasta / "variable-overrides.json")
